from __future__ import print_function
import sys
from time import time
from es_utils import es_query, format
import json
from cmsutils import MachineCPUCount, MachineMemoryGB

def getExternalsESstats(cmsdist='*', arch='*', lastNdays=7, page_size=0):
    stats = es_query(index='externals_stats_summary_testindex*',
                     query=format('cmsdist:%(cmsdist_branch)s AND architecture:%(architecture)s',
                                  cmsdist_branch=str(cmsdist),
                                  architecture=arch),
                     start_time=1000*int(time()-(86400*lastNdays)),
                     end_time=1000*int(time()),scroll=True)
    return stats['hits']['hits']

# get a dict of stats with externals name as keys
def orderStatsByName(externalsStats=None):    
    namedStats = {}
    for element in externalsStats:
        ext_name = element["_source"]["name"]
        if ext_name not in namedStats:
            namedStats[ext_name] = list()
        namedStats[ext_name].append(element["_source"])
    # order by timestamp
    for ext in namedStats:
        namedStats[ext] = sorted(namedStats[ext], key=lambda x: x["@timestamp"], reverse=True)
    return namedStats

# create a default github file with stats so if elastic search fails, try to get it

class ResourceManager(object):
    def __init__(self, architecture, cmsdist_branch, cpu_percent_usage, memory_percent_usage, njobs, lastNdays):
        self.machineResources = { "total": {"cpu_75": cpu_percent_usage*MachineCPUCount, "rss_75" : memory_percent_usage*MachineMemoryGB*10737418 },
                                  "available": {"cpu_75": cpu_percent_usage*MachineCPUCount, "rss_75" : memory_percent_usage*MachineMemoryGB*10737418 } }
        self.externalsStats = None# get them from elastic search
        self.resourcesAllocatedForExternals = {} # resources that were alocated for given externals, say root -> "root": {"rss":"", cpu:""}
        self.jobsOrderMetric = "cpu_75" # default to cpu
        self.missingExternalsStrategy = None # runFirst, runLast
    
    def allocResourcesForExternals(self, externalsList=[]): # return ordered list for externals that can be started
        # first, strip the names from build-*++version and make a tmp name to full name dict.
        # toolfiles should not arrive here, but will also work if they do
        ext_name_to_fullname_dict = {}
        for e in externalsList:
            short_name = e.split('+')[1]
            ext_name_to_fullname_dict[short_name]=e
        externalsList_shortNames = ext_name_to_fullname_dict.keys()
        # if record for an external is not available, allocate it 1/4th of the resources and run it first
        # OR allocate all resources for each missing external, forcing it to build last. this should
        externals_to_run = []
        for ext in externalsList_shortNames:
            if ext not in self.externalsStats:
                # external is not found, this should happen only for new externals. get the first element whichever it is and change its properties
                self.externalsStats[ext] = [{"name":ext, "cpu_75":self.machineResources["total"]["cpu_75"]/4,"rss_75":self.machineResources["total"]["rss_75"]/10 }]
            externals_to_run.append(self.externalsStats[ext][0])        
        # first order them by metric and then run over to alloc resources
        externalsList_sorted = [ext for ext in sorted(externals_to_run, key=lambda x: x[self.jobsOrderMetric], reverse=True)]

        externals_to_run = []
        for ex_stats in externalsList_sorted:
            if (ex_stats["cpu_75"]<=self.machineResources["available"]["cpu_75"] and ex_stats["rss_75"]<=self.machineResources["available"]["rss_75"]):
                self.resourcesAllocatedForExternals[ex_stats["name"]] = {}
                for prm in ["rss_75", "cpu_75"]:
                    self.machineResources["available"][prm] -= ex_stats[prm]
                    self.resourcesAllocatedForExternals[ex_stats["name"]][prm] = ex_stats[prm]
                externals_to_run.append(ext_name_to_fullname_dict[ex_stats["name"]]) # this gets the full names
        return externals_to_run

    def releaseResourcesForExternal(self, external): # external name
        # get the external name only
        external = external.split('+')[1]
        for prm in ["rss_75", "cpu_75"]:
            self.machineResources["available"][prm] += self.resourcesAllocatedForExternals[external][prm]
        del self.resourcesAllocatedForExternals[external]

if __name__ == "__main__":
    # use : python getExternalsESstats.py IB/CMSSW_11_3_X/master slc7_amd64_gcc900 14
    from es_utils import get_indexes

    idxs = get_indexes()
    cmsdist = sys.argv[1]
    arch = sys.argv[2]
    days = int(sys.argv[3])
    page_size = 0
    #print(format('(NOT cpu_max:0) AND (exit_code:0) AND cmsdist:%(cmsdist_branch)s AND architecture:%(architecture)s', cmsdist_branch=str(cmsdist), architecture=arch))    
    externals_stats=getExternalsESstats(cmsdist, arch, days, page_size)
    orderedExternalsStats = orderStatsByName(externals_stats)    
    res_manager = ResourceManager(arch, cmsdist, 100, 100, 16, 30)
    res_manager.externalsStats = orderedExternalsStats
    ext_to_run = ["build-external+yoda+2.10.0-cms", "build-external+sherpa+2.10.0-cms", "build-external+rivet+2.10.0-cms", "build-external+root+2.10.0-cms", "build-external+dd4hep+2.10.0-cms", "build-external+herwigpp+2.10.0-cms", "build-external+hector+2.10.0-cms", "build-external+professor+2.10.0-cms", "build-external+py2-root_numpy+2.10.0-cms", "build-external+thepeg+2.10.0-cms", "build-external+fasthadd+2.10.0-cms"]
    print('externals before selection: \n', ext_to_run, ' in total: ', len(ext_to_run))
    print('machine resources before alocation' ,res_manager.machineResources)
    result_ext_to_run = res_manager.allocResourcesForExternals(ext_to_run)
    print('selected to run: \n', result_ext_to_run, ' in total: ', len(result_ext_to_run))
    print('allocated resources: ', res_manager.resourcesAllocatedForExternals)
    print('machine resources after alocation' ,res_manager.machineResources)
    print('release the resources:')
    for i in result_ext_to_run: res_manager.releaseResourcesForExternal(i)
    print('allocated resources: ', res_manager.resourcesAllocatedForExternals)
    print('machine resources' ,res_manager.machineResources)

    #print(externals_stats)
    #print(json.dumps(externals_stats, indent=2, sort_keys=True, separators=(',', ': ')))
    with open('stats_file.json', 'w') as sf:
        sf.write(json.dumps(externals_stats, indent=1, sort_keys=True))
    with open('stats_file_named.json', 'w') as sf:
        sf.write(json.dumps(orderStatsByName(externals_stats), indent=1, sort_keys=True))
    
