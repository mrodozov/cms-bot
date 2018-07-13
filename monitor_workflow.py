#!/usr/bin/env python
from os import system, getpid
from sys import argv, exit
from time import sleep, time
import psutil
from threading import Thread
import subprocess
import json

def run_job(job): job['exit_code']=subprocess.call(job['command'])

def update_stats(proc):
  stats = {"rss":0, "vms":0, "shared":0, "data":0, "uss":0, "pss":0,"num_fds":0,"num_threads":0, "processes":0, "cpu": 0}
  children = proc.children(recursive=True)
  clds = len(children)
  if clds==0: return stats
  stats['processes'] = clds
  for cld in children:
    try:
      mem   = cld.memory_full_info()
      fds   = cld.num_fds()
      thrds = cld.num_threads()
      cld.cpu_percent(interval=None)
      sleep(0.1)
      cpu   = int(cld.cpu_percent(interval=None))
      stats['num_fds'] += fds
      stats['num_threads'] += thrds
      stats['cpu'] += cpu
      for a in ["rss", "vms", "shared", "data", "uss", "pss"]: stats[a]+=getattr(mem,a)
    except:pass
  return stats

def monitor(stop):
  cmdline = " ".join(p.cmdline())  
  if "cmsDriver.py " in  cmdline:
    print ' cmsDriver found in cmndline'
    cmdargs=cmdline.split("cmsDriver.py ",1)[1].strip()
    step=None
    if cmdargs.startswith("step"):
      step=cmdargs.split(" ")[0]
    elif ' --fileout ' in cmdargs:
      step =cmdargs.split(' --fileout ',1)[1].strip().split(" ")[0].replace("file:","").replace(".root","")
    if not "step" in step: step="step1"
  else: step=stime
  data = []
  libs_list = []
  while not stop():
    #stats = None
    try:
      stats = update_stats(p)
      if stats['processes']==0: break
      stats['time'] = int(time()-stime)      
      data.append(stats)
    except: pass
    sleep_time = 1.0-stats['processes']*0.1
    if sleep_time > 0.1: sleep(sleep_time)
  from json import dump
  stat_file =open("wf_stats-%s.json" % step,"w")
  dump(data, stat_file)
  stat_file.close()

  return

def get_shared_libs_from_list_of_strings(list_of_files=[]):
    result = []
    for itm in list_of_files:
    #    if '.so' in itm:
        result.append(itm)
    return result

def list_shared_objects_for_process(proc=None):
    #lists all opened files for a process
    ''' TODO - remember that under docker you ight NOT have lsof. And thats why it doesn't work '''
    if not proc:
        print 'no proc given !'
        return []
    childp = subprocess.Popen('lsof -p ' + str(proc), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    stout, sterr = childp.communicate()
    #now look for all the shred libs with a function
    #with open('file_for_list_openedfiles.txt') as flof:
    #    flof.write(stout)
    result = get_shared_libs_from_list_of_strings(stout.split('\n'))
    return result

def probe_for_loaded_libs(stop):
    print 'starting probing func ... '
    #get main process
    p = psutil.Process()
    chldrn_procs = p.children(recursive=True)
    #list child procs to find the cmsRun one
    child_p_num = None
    step = None
    cmdargs = None
    list_of_libs = []
    #get the right proc here and probe it for the shared libs. the proc is only one but this might not be always the case
    
    while not stop():
      print 'probing for opened so libs'
      chldrn_procs = p.children(recursive=True)
      for child_proc in chldrn_procs:
        #get step num
        cmndline = " ".join(child_proc.cmdline())
        print 'Command line is: ',cmndline
        if 'cmsDriver' in cmndline:
          cmdargs=cmndline.split("cmsDriver.py ",1)[1].strip()
        if cmdargs.startswith("step"):
          step=cmdargs.split(" ")[0]
          print 'step is ', step
        else:
          step = int(time())
        #get list of libs
        print('Child pid is {}'.format(child_proc.pid))
        child_p_num = child_proc.pid        
        list_of_libs += list_shared_objects_for_process(child_p_num)
      sleep(10)

    with open('wf_libs_list_'+str(step)+'.json', 'w') as libs_file:
      libs_file.write(json.dumps(list(set(list_of_libs)), indent=2))

    return


stop_monitoring = False

job = {'exit_code':0, 'command':'true'}
job['command']=argv[1:]
job_thd = Thread(target=run_job, args=(job,))
mon_thd = Thread(target=monitor, args=(lambda: stop_monitoring,))
probe_thd = Thread(target=probe_for_loaded_libs, args=(lambda : stop_monitoring,))
job_thd.start()
sleep(1)
mon_thd.start()
probe_thd.start()
job_thd.join()
stop_monitoring = True
mon_thd.join()
probe_thd.join()
exit(job['exit_code'])

#sort futher on 1. executable (cmsRun) 2. in memory (mem substr) 3. type of file extension (.so)
