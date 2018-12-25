from os.path import dirname, abspath
from sys import argv
from commands import getstatusoutput
from JobsConstructor import JobsConstructor
from JobsManager import JobsManager
from JobsProcessor import JobsProcessor
from threading import Event
import Queue
from optparse import OptionParser
import json
from multiprocessing import cpu_count
from CustomFunctions import relval_test_process, process_relval_workflow_step, cpu_priority_sorting_function
import psutil

import os
import sys


from cmssw_known_errors import get_known_errors

if __name__ == "__main__":

    parser = OptionParser(usage="%prog ")
    parser.add_option("-r", "--release", dest="release", help="Release filter", type=str, default="*")
    parser.add_option("-a", "--architecture", dest="arch",
                      help="SCRAM_ARCH filter. Production arch for a release cycle is used if found otherwise slc6_amd64_gcc530",
                      type=str, default=None)
    parser.add_option("-d", "--days", dest="days", help="Files access in last n days", type=int, default=7)
    parser.add_option("-j", "--job", dest="job", help="Parallel jobs to run", type=int, default=4)
    parser.add_option("-p", "--page", dest="page_size",
                      help="Page size, default 0 means no page and get all data in one go", type=int, default=0)
    opts, args = parser.parse_args()
    opts.release = "CMSSW_10_4_CLANG"
    opts.arch = "slc7_amd64_gcc700"
    '''
    if not opts.arch:
        if opts.release == "CMSSW_10_4_X":
            opts.arch = "slc7_amd64_gcc700"
        else:
            script_path = abspath(dirname(argv[0]))
            err, out = getstatusoutput(
                "grep 'RELEASE_QUEUE=%s;' %s/config.map | grep -v 'DISABLED=1;' | grep 'PROD_ARCH=1;' | tr ';' '\n' | grep 'SCRAM_ARCH=' | sed 's|.*=||'" % (
                opts.release, script_path))
            if err:
                opts.arch = "slc7_amd64_gcc700"
            else:
                opts.arch = out
    '''
    ''' gets the CL arguments '''

    print opts.release, opts.arch, opts.days

    #opts.release = 'CMSSW_9_3_X*'
    #opts.arch = 'slc6_amd64_gcc630'
    #opts.days = 7
    opts.page_size = 0
    wf_list = argv[1]

    #with open('resources/wf_slc6_530_1of5.txt') as wf_list_file:
        #wf_list = wf_list_file.read().replace('\n', ',')
        #wf_list = wf_list[:-1]

    ''' here the program is tested  '''

    avg_mem = 0.90*psutil.virtual_memory()[0]
    avg_cpu = 200*cpu_count()
    wf_limit = 1000

    #print psutil.virtual_memory()[]
    #exit(0)

    toProcessQueue = Queue.Queue()
    processedTasksQueue = Queue.Queue()

    getNextJobsEvent = Event()
    finishJobsEvent = Event()

    known_errors = get_known_errors(opts.release, opts.arch, 'relvals')
    #print known_errors
    
    jc = JobsConstructor(None, known_errors)
    matrixMap =jc.constructJobsMatrix(opts.release, opts.arch, opts.days, opts.page_size, wf_list, wf_limit, "/Users/mrodozov/Projects/cms-bot/steps")
    result = jc.getWorkflowStatsFromES(release=opts.release, arch=opts.arch, lastNdays=7, page_size=10000)
    #print json.dumps(result, indent=2, sort_keys=True, separators=(',', ': '))

    print matrixMap

    ''' up to here it constructs the jobs stats'''

    #exit(0)

    jm = JobsManager(matrixMap)
    jm.toProcessQueue = toProcessQueue
    jm.processedQueue = processedTasksQueue
    jm.availableMemory = avg_mem
    jm.availableCPU = avg_cpu

    jp = JobsProcessor(toProcessQueue, processedTasksQueue)
    jp.allJobs = jm.jobs
    jp.allJobs_lock = jm.jobs_lock

    jm.getNextJobsEvent = getNextJobsEvent
    jm.finishJobsEvent = finishJobsEvent

    jm.job_process_function = relval_test_process
    jm.jobs_sorting_function = cpu_priority_sorting_function

    jm.putJobsOnProcessQueue.start()
    jp.start()
    jm.getProcessedJobs.start()

    print 'put jobs on queue tries to join'
    jm.putJobsOnProcessQueue.join()

    print 'processor tries to join:'
    jp.join()

    print 'finish jobs tries to join'
    jm.getProcessedJobs.join()
    print 'finish jobs joined'

    print jm.results

    jm.writeResultsInFile('jobs_results_ideRun.json')

    #print wf_list
    
    #add on matrix construct and wf stats for them

