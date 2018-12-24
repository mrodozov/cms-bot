__author__ = 'mrodozov@cern.ch'
'''
this class instances are responsible to construct the jobs structure (json object) given list of workflows as input
for this the class has to 
1. run runTheMatrix in dummy mode
2. get history data from elastic search
3. construct the object and pass it to whoever needs to use it
'''

import json
from Singleton import Singleton
from time import time
import subprocess
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CMS_BOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR,'..'))
sys.path.insert(0,CMS_BOT_DIR)
sys.path.insert(0,SCRIPT_DIR)

from es_utils import get_payload, es_query, format

class JobsConstructor(object):

    __metaclass__ = Singleton

    def __init__(self, workflows_list=None, cmssw_known_errors={}):

        self._workflows = workflows_list
        self._known_errors = cmssw_known_errors

    def _format(self, s, **kwds):
        return s % kwds

    def getWorkflowStatsFromES(self, release='*', arch='*', lastNdays=7, page_size=10000):
        stats = es_query(index='relvals_stats_*',
                 query=format('(NOT cpu_max:0) AND (exit_code:0) AND release:%(release_cycle)s AND architecture:%(architecture)s',
                              release_cycle=release+"_*",
                              architecture=arch
                             ),
                 start_time=1000*int(time()-(86400*lastNdays)),
                 end_time=1000*int(time()))
        return stats['hits']['hits']
        
    def getJobsCommands(self, workflow_matrix_list=None,workflows_limit=None, workflows_dir="/Users/mrodozov/Projects/cms-bot/steps/"): #os.environ["CMSSW_BASE"]+"/pyRelval/"

        #run runTheMatrix and parse the output for each workflow, example results structure in resources/wf.json
        #for now, get it from the file resources/wf.json
        #run_matrix_process = subprocess.Popen('voms-proxy-init;runTheMatrix.py -l '+workflow_matrix_list+' -i all --maxSteps=0 -j 20',
        #                                      shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        #                                      close_fds=True)
        #stdout, stderr = run_matrix_process.communicate()
        #wf_base_folder = '/build/cmsbld/mrodozov/testScheduler/CMSCIResourceBalancer/'
        wf_base_folder = workflows_dir
        #wf_base_folder = 'resources/wf_folders/'
        wf_folders = [fld for fld in os.listdir(wf_base_folder) if os.path.isdir(os.path.join(wf_base_folder, fld))]
        #print os.listdir(wf_base_folder)
        matrix_map = {}
        #print wf_folders
        counter = 0
        for f in wf_folders:
            #print f
            wf_id = f.split('_')[0]

            if not os.path.exists(os.path.join(wf_base_folder, f, 'wf_steps.txt')):
                continue
            matrix_map[wf_id] = {}
            with open(os.path.join(wf_base_folder, f, 'wf_steps.txt')) as wf_file:
                for line in wf_file.readlines():
                    stepID, stepCommands = line.split(':', 1)
                    #print stepID
                    #print stepCommands
                    # print the commands after each step in cmdLog
                    matrix_map[wf_id][stepID] = {'description':[], 'commands': 'cd '+ wf_base_folder + ';' + stepCommands,
                                                 'results_folder': os.path.join(wf_base_folder, f)}
            if wf_id in self._known_errors:
                with open(os.path.join(wf_base_folder, f, 'known_errors.json'),'w') as known_errs_file:
                    known_errs_file.write(json.dumps(self._known_errors[wf_id]))

            counter += 1
            if workflows_limit and counter > workflows_limit:
                break
            #print wf_id
        #print json.dumps(matrix_map, indent=1, sort_keys=True)

        return matrix_map


    def constructJobsMatrix(self, release, arch, days, page_size, workflow_matrix_list, wf_limit,wfs_basedir):
        matrixMap = self.getJobsCommands(workflow_matrix_list, wf_limit, wfs_basedir)
        #print matrixMap
        jobs_stats = self.getWorkflowStatsFromES(release, arch, days, page_size)
        #for local test get the stats from a file
	'''
        with open('resources/wf.json') as matrixFile:
            matrixMap = json.loads(matrixFile.read())
        with open('resources/exampleESqueryResult.json') as esQueryFromFile:
            jobs_stats = json.loads(esQueryFromFile.read())[0]['hits']['hits']
	'''
        ESworkflowsData = jobs_stats

        for i in ESworkflowsData:
            if i['_source']['workflow'] in matrixMap and i['_source']['step'] in matrixMap[i['_source']['workflow']]:
                matrixMap[i['_source']['workflow']][i['_source']['step']]['description'].append(i['_source'])

        # print json.dumps(matrixMap, indent=2, sort_keys=True, separators=(',', ': ')) # GOOD Anakin, GOOOOOOD

        for wf_id in matrixMap:
            for step_id in matrixMap[wf_id]:
                nKeys = len(matrixMap[wf_id][step_id]['description'])
                countTime = 0
                countMem = 0
                cpuUsage = 0
                for rec in matrixMap[wf_id][step_id]['description']:
                    countTime += int(rec['time'])
                    countMem += int(rec['rss_75'])
                    cpuUsage += int(rec['cpu_avg'])
                if nKeys > 0:
                    matrixMap[wf_id][step_id]['avg_time'] = countTime / nKeys
                    matrixMap[wf_id][step_id]['avg_mem'] = countMem / nKeys
                    matrixMap[wf_id][step_id]['avg_cpu'] = cpuUsage / nKeys
                else:
                    matrixMap[wf_id][step_id]['avg_time'] = 21600
                    matrixMap[wf_id][step_id]['avg_mem'] = 4500000000
                    matrixMap[wf_id][step_id]['avg_cpu'] = 400

        return matrixMap

if __name__ == "__main__":


    # fix ES queries

    opts = None
    release = 'CMSSW_10_4_X'
    arch = 'slc7_amd64_gcc700'
    days = 7
    page_size = 0
    jk = JobsConstructor()

    matrix_map = jk.getJobsCommands()
    #print json.dumps(matrix_map, indent=2, sort_keys=True, separators=(',', ': '))
    result = jk.getWorkflowStatsFromES(release=release, arch=arch, lastNdays=7, page_size=10000)
    print json.dumps(result, indent=2, sort_keys=True, separators=(',', ': '))
    
    exit(0)

    wf_list = None
    with open('resources/wf_slc6_530.txt') as wf_list_file:
        wf_list = wf_list_file.read().replace('\n', ',')
        wf_list = wf_list[:-1]
    
    known_errors = get_known_errors(release, arch, 'relvals')

    jc = JobsConstructor(wf_list)
    jc.getJobsCommands(wf_list)

    #print wf_list

    limit = 20

    json_out = jc.constructJobsMatrix(release, arch, days, page_size, wf_list, limit,os.environ["CMSSW_BASE"]+"/pyRelval/")
    print json.dumps(json_out, indent=2, sort_keys=True, separators=(',', ': '))
    print len(json_out)
