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

# resources functions are kept in cmsutils.py which is basically reading nproc and free outputs instead of using psuitl or anything else
# memory is used as it is in (bytes?) , cpu is multiplied by 1.5 (use 50% more) when used to run the relvals
# ES stats are read and dump in all.jobs with the hits and then processed with es_workflow_stats from es_utils
# the result is the jobs.json which contains time cpu rss rss_avg rss_max cpu_avg cpu_max where the cpu and rss are the average of the cpu_75 and rss_75 from all hits
# https://github.com/cms-sw/cms-bot/blob/master/es_utils.py#L165
# im writing this as comment so I don't have to read it in code every time :/
# using cpu_75 and rss_75 for memory and cpu metrics
# Ordering of which job goes first by what metric in jobs/jobscheduler.py
# https://github.com/cms-sw/cms-bot/blob/master/jobs/jobscheduler.py#L79

class ResourceManager(object):
    def __init__(self, architecture, cmsdist_branch, cpu_percent_usage, memory_percent_usage, njobs, lastNdays):
        self.machineResources = { "total": {"cpu_75": cpu_percent_usage*MachineCPUCount, "rss_75" : memory_percent_usage*MachineMemoryGB*10737418 },
                                  "available": {"cpu_75": cpu_percent_usage*MachineCPUCount, "rss_75" : memory_percent_usage*MachineMemoryGB*10737418 } }
        self.externalsStats = None# get them from elastic search
        self.resourcesAllocatedForExternals = {} # resources that were alocated for given externals, say root -> "root": {"rss":"", cpu:""}
        self.jobsOrderMetric = "cpu_75" # default to cpu
    
    def allocResourcesForExternals(self, externalsList=[]): # return ordered list for externals that can be started
        # first, strip the names from build-*++version and make a tmp name to full name dict.
        # toolfiles should not arrive here, but will also work if they do
        ext_name_to_fullname_dict = {}
        for e in externalsList:
            short_name = e.split('+')[1]
            ext_name_to_fullname_dict[short_name]=e
        externalsList_shortNames = ext_name_to_fullname_dict.keys()
        # if record for an external is not available, allocate it 1/4th of the resources and run it first
        # OR allocate all resources for each missing external, forcing it to build last
        
        externals_to_run = []
        for ext in externalsList_shortNames:
            # find the latest record by ordering the records by timestamp
            ex_stats = self.externalsStats[ext][0]
            if (ex_stats["cpu_75"] <= self.machineResources["available"]["cpu_75"] 
                and ex_stats["rss_75"] <= self.machineResources["available"]["rss_75"]):
                self.resourcesAllocatedForExternals[ext] = {}
                for prm in ["rss_75", "cpu_75"]:
                    self.machineResources["available"][prm] -= ex_stats[prm]
                    self.resourcesAllocatedForExternals[ext][prm] = ex_stats[prm]
                externals_to_run.append(ex_stats)
        return [ext["name"] for ext in sorted(externals_to_run, key=lambda x: x[self.jobsOrderMetric], reverse=True)]

    def releaseResourcesForExternal(self, external): # external name
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
    ext_to_run = ["yoda", "sherpa", "rivet", "root", "dd4hep", "herwigpp", "hector"]
    result_ext_to_run = res_manager.allocResourcesForExternals(ext_to_run)
    print(result_ext_to_run)
    print('allocated resources: ', res_manager.resourcesAllocatedForExternals)
    print('machine resources' ,res_manager.machineResources)
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
    
