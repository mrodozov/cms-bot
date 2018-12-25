__author__ = 'mrodozov@cern.ch'
'''
This class instance(singleton) manages jobs ordering
'''
import json
import os
import subprocess
import sys
import time
from threading import Lock, Thread, Semaphore
from time import sleep

from Singleton import Singleton

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CMS_BOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, CMS_BOT_DIR)
sys.path.insert(0, os.path.join(CMS_BOT_DIR, 'jobs'))

# from workflow_final import upload_logs

'''
method putNextJobsOnQueue may need to use another lock
whenever it starts to prevent method getFinishedJobs while loop to
get called more than once while putNextJobsOnQueue is still
executing 

'''

from CustomFunctions import relval_test_process, process_relval_workflow_step, getWorkflowDuration, writeWorkflowLog, worklowIsStartingFunc, finilazeWorkflow, stepIsStartingFunc, stepIsFinishingFunc

class workerThread(Thread):
    def __init__(self, target, *args):
        super(workerThread, self).__init__()
        self._target = target
        self._args = args
        # self.name = str(args[0] + ' ' + args[1])
        self.resultQueue = None
        self.getNextJobs = None

    def run(self):
        result = self._target(*self._args)
        # put the result when the task is finished
        # result = result+' '+self.name
        self.resultQueue.put(result)


class JobsManager(object):
    __metaclass__ = Singleton

    def __init__(self, jobs=None):

        self.jobs = jobs
        self.jobs_result_folders = {}
        self.started_jobs = None
        self.results = {}
        self.availableMemory = None
        self.availableCPU = None
        self.jobs_lock = Lock()  # lock when touching jobs structure
        self.started_jobs_lock = Lock()
        self.results_lock = Lock()  # lock when touching results structure
        self.error_codes_map = None
        self.translate_exit_codes = False  # set this flag to true to translate codes

        ''' 
        add the thread jobs that put jobs on execution queue
        and finilizes them here
        '''

        self.started_jobs = []  # jobs already started
        self.putJobsOnProcessQueue = Thread(target=self.putJobsOnQueue)
        self.getProcessedJobs = Thread(target=self.getFinishedJobs)
        self.toProcessQueue = None
        self.processedQueue = None
        self.getNextJobsEvent = None
        self.counter = Semaphore()

        '''
        API calls provided externally as functions that would be called with specific arguments
        '''

        # TODO - last - f iface -> the object calling the functions is the first argument, and then the rest

        self.job_process_function = None # to be given later
        self.workflowIsStarting = worklowIsStartingFunc
        self.workflowIsFinishing = finilazeWorkflow
        self.stepIsStarting = stepIsStartingFunc
        self.stepIsFinishing = stepIsFinishingFunc
        self.jobs_sorting_function = None #

    '''
    methods to check resources availability
    '''

    def checkIfEnoughMemory(self, mem_value=0):
        return self.availableMemory > mem_value
        # or use a record of the remaining memory

    def checkIfEnoughCPU(self, cpu_value=0):
        return self.availableCPU > cpu_value

    '''
    put jobs for processing methods
    '''

    def putJobsOnQueue(self):

        while True:
            if not self.jobs:
                print 'to process queue completed, breaking put jobs on queue', '\n'
                break

            # get jobs from the structure put them on queue to process
            self.counter.acquire()  # acquire resource once, the finishing thread would release it for each finished job
            next_jobs = self.getNextJobs()
            print 'put jobs on queue getting next jobs:', '\n'  # , next_jobs
            self.putNextJobsOnQueue(next_jobs)

    def getNextJobs(self, sort_function=None):
        next_jobs = []
        with self.jobs_lock:
            for i in self.jobs:

                if not self.jobs[i].keys():
                    continue
                '''
                check if the prev job had finished with exit != 0 and if it did, 
                '''

                prev_exit = 0
                with self.results_lock:
                    if i in self.results:
                        for s in self.results[i]:
                            if self.results[i][s]['exit_code'] is not 0:
                                prev_exit = self.results[i][s]['exit_code']
                                break

                current_step = sorted(self.jobs[i].keys())[0]
                if i not in self.jobs_result_folders:
                    self.jobs_result_folders[i] = self.jobs[i][current_step]['results_folder']
                cumulative_time = sum([self.jobs[i][j]['avg_time'] for j in self.jobs[i]])
                element = (i, current_step, cumulative_time, self.jobs[i][current_step]['avg_time'],
                           self.jobs[i][current_step]['avg_mem'], self.jobs[i][current_step]['avg_cpu'],
                           self.jobs[i][current_step]['commands'], prev_exit)

                next_jobs.append(element)
                # print i, j, self.jobs[i][j]['avg_time']
        return self.jobs_sorting_function(self, next_jobs)

    def putNextJobsOnQueue(self, jobs=None):
        print 'put next jobs on queue', '\n'
        for j in jobs:
            print j[0], j[1]

        for job in jobs:

            if job[0] in self.started_jobs or not self.checkIfEnoughMemory(job[4]) or not self.checkIfEnoughCPU(job[5]):

                resource_not_available = []
                if job[0] in self.started_jobs:
                    resource_not_available.append('prev step not finished')
                if not self.checkIfEnoughMemory(job[4]):
                    resource_not_available.append('not enough memory')
                if not self.checkIfEnoughCPU(job[5]):
                    resource_not_available.append('not enough cpu')

                print 'skipping job', job[0], job[1], 'because ', ','.join(resource_not_available)

                continue

            with self.started_jobs_lock:
                self.started_jobs.append(job[0])
                self.availableMemory = self.availableMemory - job[4]
                self.availableCPU = self.availableCPU - job[5]
                thread_job = workerThread(self.job_process_function, job)
                #thread_job = workerThread(relval_test_process, job)
                '''
                callbacks calls
                '''
                if job[0] not in self.results:
                    # its the first step of the wf, execute one time pre wf callback
                    self._workflowIsStarting(self ,job)
                # and once per step
                self._stepIsStarting(self, job)
                self.toProcessQueue.put(thread_job)

            self._removeJobFromWorkflow(job[0], job[1])
            # print self.jobs

        print 'jobs putted on queue'

    '''
    finishing jobs after process
    '''

    def getFinishedJobs(self):

        while True:

            print 'get finished jobs', '\n'
            # print 'jobs from finished jobs', '\n', self.jobs
            finishedJob = self.processedQueue.get()  # gets the return value from thread function, i.e. wf step result
            self.finishJob(finishedJob)
            # print finishedJob['id']
            self.processedQueue.task_done()
            self.counter.release()  # release the lock for each finished job, putJobsOnQueue retries to put new jobs

            print 'finished get finished jobs for ', finishedJob['id'], '\n'

            if not self.jobs and not self.started_jobs:
                print 'breaking get finished jobs'
                break

    def finishJob(self, job=None):
        print 'finish', job['id'], job['step'], job['exit_code'], job['mem'], job['cpu']
        # callback call when step is finished
        self._stepIsFinishing(self, job)
        self._insertRecordInResults(job)
        # insert the record before removing the job since it might remove the entire job

        with self.started_jobs_lock:
            self.availableMemory += job['mem']
            self.availableCPU += job['cpu']
            self.started_jobs.remove(job['id'])
            print 'job removed: ', job['id']

        # finish the workflow if the step was the last

        with self.jobs_lock:
            if not job['id'] in self.jobs:
                print 'finalize wf:', job['id']
                with self.results_lock:
                    self.results[job['id']]['finishing_exit'] = 'finished'
                    job_results = self.results[job['id']]
                    current_job_folder = self.jobs_result_folders[job['id']]
                    # callback call when the entire workflow is finished
                    self._workflowIsFinishing(self, job)

    '''
    protected methods
    '''

    def _removeJobFromWorkflow(self, jobID=None, stepID=None):
        with self.jobs_lock:
            if jobID in self.jobs and stepID in self.jobs[jobID]:
                if len(self.jobs[jobID]) == 1:
                    self._removeWorkflow(jobID)
                else:
                    del self.jobs[jobID][stepID]

    def _removeWorkflow(self, wf_id=None):
        if wf_id in self.jobs:
            del self.jobs[wf_id]

    def _insertRecordInResults(self, result=None):

        with self.results_lock:
            if not result['id'] in self.results:
                self.results[result['id']] = {}

            self.results[result['id']][result['step']] = {'exit_code': result['exit_code'], 'stdout': result['stdout'],
                                                          'stderr': result['stderr'], 'start_time': result['startTime'],
                                                          'end_time': result['endTime'],
                                                          'exec_time': result['endTime'] - result['startTime']}

    def writeResultsInFile(self, filen=None):
        with self.results_lock:
            with open(filen, 'w') as results_file:
                results_file.write(json.dumps(self.results, indent=1, sort_keys=True))

    '''
    callback methods to be called 
    '''

    def _workflowIsStarting(self, *args):
        #print 'wf is starting'
        if self.workflowIsStarting:
            self.workflowIsStarting(*args)

    def _workflowIsFinishing(self, *args):
        #print 'wf is finishing, job id: ', args[0]
        if self.workflowIsFinishing:
            self.workflowIsFinishing(*args)

    def _stepIsStarting(self, *args):
        #print 'step is starting: ',
        if self.stepIsStarting:
            self.stepIsStarting(*args)

    def _stepIsFinishing(self, *args):
        print args
        if self.stepIsFinishing:
            self.stepIsFinishing(*args)


''' 
the task list 
'''

if __name__ == "__main__":
    jobs_result = {
        "finishing_exit": "finished",
        "step1": {
            "exit_code": 0,
            "stderr": None,
            "stdout": ""
        },
        "step2": {
            "exit_code": 0,
            "stderr": None,
            "stdout": ""
        },
        "step3": {
            "exit_code": 0,
            "stderr": None,
            "stdout": ""
        }
    }

    keys_list = sorted(jobs_result, reverse=False)

    # given_wf_folder = 'resources/finished_wf_folders/matrix/2.0_ProdTTbar+ProdTTbar+DIGIPROD1+RECOPROD1'
    given_wf_folder = 'resources/finished_wf_folders/matrix/1.0_ProdMinBias+ProdMinBias+DIGIPROD1+RECOPROD1'

    writeWorkflowLog(given_wf_folder, jobs_result)

    getWorkflowDuration(given_wf_folder)

    pass
