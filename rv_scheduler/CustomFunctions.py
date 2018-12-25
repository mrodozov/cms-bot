import time
from time import sleep
import json
import os
import subprocess
import sys
import time
from operator import itemgetter
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CMS_BOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))


def relval_test_process(job=None):
    # unpack the job and execute
    # jobID, jobStep, jobCumulativeTime, jobSelfTime, jobCommands = job.items()
    jobID = job[0]
    jobStep = job[1]
    jobCumulativeTime = job[2]
    jobSelfTime = job[3]
    jobMem = job[4]
    jobCPU = job[5]
    jobCommands = job[6]
    prevJobExit = job[7]
    jobSelfTime = 0.001

    startTime = int(time.time())

    while True:
        # print 'eta: ', jobID, jobStep, jobSelfTime
        sleep(jobSelfTime)
        jobSelfTime -= 0.001
        if 0 > jobSelfTime:
            print 'breaking'
            break

    # have some delay for the test
    sleep(0.2)

    endTime = int(time.time())

    # return {'id': jobID, 'step': jobStep, 'exit_code': 0, 'mem': int(jobMem)}
    return {'id': jobID, 'step': jobStep, 'exit_code': '0', 'mem': int(jobMem), 'cpu': int(jobCPU),
            'stdout': 'notRun', 'stderr': 'notRun', 'startTime': startTime, 'endTime': endTime}

def process_relval_workflow_step(job=None):
    # unpack the job and execute
    # jobID, jobStep, jobCumulativeTime, jobSelfTime, jobCommands = job.items()
    jobID = job[0]
    jobStep = job[1]
    jobCumulativeTime = job[2]
    jobSelfTime = job[3]
    jobMem = job[4]
    jobCPU = job[5]
    jobCommands = job[6]
    prevJobExit = job[7]
    # jobCommands = 'ls'

    exit_code = 0

    if prevJobExit is not 0:
        return {'id': jobID, 'step': jobStep, 'exit_code': -1, 'mem': int(jobMem), 'cpu': int(jobCPU),
                'stdout': 'notRun', 'stderr': 'notRun', 'startTime': 0, 'endTime': 0}

    start_time = int(time.time())

    child_process = subprocess.Popen(jobCommands, shell=True)
    # , stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    stdout = ''
    stderr = ''
    # child_process.communicate()
    # exit_code = child_process.returncode
    exit_code = os.waitpid(child_process.pid, 0)[1]
    # to test the non zero exit code

    endTime = int(time.time())

    return {'id': jobID, 'step': jobStep, 'exit_code': exit_code, 'mem': int(jobMem), 'cpu': int(jobCPU),
            'stdout': stdout, 'stderr': stderr, 'startTime': start_time, 'endTime': endTime}
    # start a subprocess, return it's output


def getWorkflowDuration(workflowFolder=None):
    total_time = 0
    for i in os.listdir(workflowFolder):
        if i.find('wf_stats-') is not -1:
            with open(os.path.join(workflowFolder, i), 'r') as wf_stats_file:
                wf_stats_obj = json.loads(wf_stats_file.read())
                total_time += wf_stats_obj[-1]['time']

    print total_time
    with open(os.path.join(workflowFolder, 'time.log'), 'w') as timelog_file:
        timelog_file.write(str(total_time))

    return total_time


def writeWorkflowLog(workflowFolder=None, workflowLogsJson=None):
    result_keys = sorted(workflowLogsJson, reverse=False)
    result_keys.remove('finishing_exit')
    workflow_subfolder = workflowFolder.split('/')[-1]
    print 'workflow subfolder is:', workflow_subfolder
    steps_strings = []
    time_string = ''
    exit_codes = []
    passed = []
    failed = []
    # print workflow_subfolder
    for i in result_keys:

        # print i, workflowLogsJson[i]
        if workflowLogsJson[i]['exit_code'] is 0:
            steps_strings.append(i + '-PASSED')
            passed.append('1')
            failed.append('0')
            exit_codes.append('0')
        elif workflowLogsJson[i]['exit_code'] is 'notRun':
            steps_strings.append(i + '-NOTRUN')
            passed.append('0')
            failed.append('0')
            exit_codes.append('0')
        else:
            steps_strings.append(i + '-FAILED')
            passed.append('0')
            failed.append('1')
            exit_codes.append(str(workflowLogsJson[i]['exit_code']))

    output_log = workflow_subfolder + ' ' + \
                 ' '.join(steps_strings) + ' ' + \
                 ' - time;' + ' ' + \
                 'exit:' + ' ' + \
                 ' '.join(exit_codes) + ' ' + \
                 '\n' + ' ' + \
                 ' '.join(passed) + ' test passed,' + ' ' + \
                 ' '.join(failed) + ' tests failed'
    print output_log

    with open(os.path.join(workflowFolder, 'workflow.log'), 'w') as wflog_output:
        wflog_output.write(output_log)
    # put also the hostname
    with open(os.path.join(workflowFolder, 'hostname'), 'w') as hostname_output:
        hostname_output.write(os.uname()[1])


def getAverageStatsFromJSONlogs(aLog=None):
    print aLog


'''
callbacks to be hooked
'''


def worklowIsStartingFunc(caller_obj, job_obj):
    workflowID = job_obj[0]
    wf_base_folder = caller_obj.jobs_result_folders[workflowID]
    return
    print 'print from wf is starting'
    wfs_base = wf_base_folder.rsplit('/', 1)[0]
    print workflowID, wf_base_folder, wfs_base
    job_description = None
    with open(os.path.join(wfs_base, 'jobs.json'), 'r') as jobs_file:
        stats_obj = json.loads(jobs_file.read())
        for obj in stats_obj['jobs']:
            # print 'object is ', obj
            if 'name' in obj and obj['name'] == workflowID:
                print 'object is ', obj
                job_description = obj
                break
    if job_description:
        num_of_jobs = len(job_description['commands'])
        jobs_commands = job_description['commands']
        comm_num = 0
        new_jobs_commnds = []
        for comm in jobs_commands:
            comm['jobid'] = workflowID + '(' + str(comm_num + 1) + '/' + str(num_of_jobs) + ')'
            comm['state'] = 'Pending'
            comm['exec_time'] = 0
            comm['start_time'] = 0
            comm['end_time'] = 0
            comm['exit_code'] = -1
            new_jobs_commnds.append(comm)
            comm_num += 1
        job_description['commands'] = new_jobs_commnds
        job_description['state'] = 'Done'
        with open(os.path.join(wfs_base, workflowID + '.json'), 'w') as job_file:
            job_file.write(json.dumps(job_description, indent=1, sort_keys=True))


def finilazeWorkflow(caller_obj, job_obj):
    workflowID = job_obj['id']
    wf_base_folder = caller_obj.jobs_result_folders[workflowID]
    job_results = caller_obj.jobs_result_folders[workflowID]
    return
    print 'wf duration (all steps): ', getWorkflowDuration(wf_base_folder)
    print workflowID, wf_base_folder, job_results
    # writeWorkflowLog(wf_base_folder, job_results) #finishing function will fix this
    print 'finishing from callback'
    wfs_base = wf_base_folder.rsplit('/', 1)[0]
    steps_keys = job_results.keys()
    steps_keys.remove('finishing_exit')
    steps_keys = sorted(steps_keys)
    print 'sorted keys are: ', steps_keys
    wf_stats = {}
    with open(os.path.join(wfs_base, workflowID + '.json'), 'r') as job_file:
        wf_stats = json.loads(job_file.read())
    cmmnd_cntr = 0
    new_cmmnds = []
    for cmmnd in wf_stats['commands']:
        cmmnds_element = cmmnd
        cmmnds_element['exit_code'] = job_results[steps_keys[cmmnd_cntr]]['exit_code']
        cmmnds_element['start_time'] = job_results[steps_keys[cmmnd_cntr]]['start_time']
        cmmnds_element['end_time'] = job_results[steps_keys[cmmnd_cntr]]['end_time']
        cmmnds_element['exec_time'] = job_results[steps_keys[cmmnd_cntr]]['exec_time']
        new_cmmnds.append(cmmnds_element)
        cmmnd_cntr += 1

    wf_stats['commands'] = new_cmmnds
    with open(os.path.join(wfs_base, workflowID + '.json'), 'w') as job_file:
        job_file.write(json.dumps(wf_stats, indent=1, sort_keys=True))

    with open(os.path.join(wf_base_folder, 'hostname'), 'w') as hostname_output:
        hostname_output.write(os.uname()[1])

    os.chdir(wfs_base)
    # this is weird, try to put it in a function only. or put it in a try catch
    p = subprocess.Popen("%s/jobs/workflow_final.py %s" % (CMS_BOT_DIR, workflowID + '.json'), shell=True)
    e = os.waitpid(p.pid, 0)[1]
    if e: exit(e)


def stepIsStartingFunc(caller_obj, job_obj):
    print 'print from step is starting'
    workflowID = job_obj[0]
    workflowStep = job_obj[1]
    wf_base_folder = caller_obj.jobs_result_folders[workflowID]
    print workflowID, workflowStep, wf_base_folder
    wfs_base = wf_base_folder.rsplit('/', 1)[0]
    # with open(os.path.join(wfs_base, workflowID+'.json'),'a') as job_file:
    #    job_file.write('step '+ workflowStep + ' is starting \n')


def stepIsFinishingFunc(caller_obj, job_obj):
    print 'jobs details', job_obj
    workflowID = job_obj['id']
    workflowStep = job_obj['step']
    wf_base_folder = caller_obj.jobs_result_folders[workflowID]
    print workflowID, workflowStep, wf_base_folder
    wfs_base = wf_base_folder.rsplit('/', 1)[0]
    print 'print from step is finishing'

    # with open(os.path.join(wfs_base, workflowID+'.json'),'a') as job_file:
    #    job_file.write('step '+ workflowStep + ' is finishing \n')

'''
end of callbacks. you are shooting a fly with bazooka here. whatever
'''

'''
jobs sorting functions
'''


def cpu_priority_sorting_function(caller_obj, next_jobs):
    return sorted(next_jobs, key=itemgetter(2), reverse=True)