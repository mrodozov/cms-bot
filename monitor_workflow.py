#!/usr/bin/env python
from os import system, getpid
from sys import argv, exit
from time import sleep, time
import psutil
from threading import Thread
import subprocess
from optparse import OptionParser

def run_job(job):
  job['exit_code']=subprocess.call(job['command'], shell=job['command_is_string'])

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

def monitor(stop, st_file_name= None):
  stime = int(time())
  p = psutil.Process(getpid())
  cmdline = " ".join(p.parent().cmdline())
  if "cmsDriver.py " in  cmdline:
    cmdargs=cmdline.split("cmsDriver.py ", 1)[1].strip()
    step=None
    if cmdargs.startswith("step"):
      step=cmdargs.split(" ")[0]
    elif ' --fileout ' in cmdargs:
      step =cmdargs.split(' --fileout ',1)[1].strip().split(" ")[0].replace("file:","").replace(".root","")
    if not "step" in step: step="step1"
  else: step=stime
  data = []
  while not stop():
    try:
      stats = update_stats(p)
      if stats['processes']==0: break
      stats['time'] = int(time()-stime)
      data.append(stats)
    except: pass
    sleep_time = 1.0-stats['processes']*0.1
    if sleep_time>0.1: sleep(sleep_time)
  from json import dump
  if st_file_name: step = st_file_name # change the file name
  stat_file =open("wf_stats-%s.json" % step,"w")
  dump(data, stat_file)
  stat_file.close()
  return

if __name__ == "__main__":

  stats_file_name = None
  architecture = None #TODO decide how to use the arch if available, put it in the file name or wut
  cmmnd = None
  cmmnd_is_string = False

  if "-c" in argv[1:] or "--command" in argv[1:]:
    parser = OptionParser(usage="%prog -p| --package <package-being-built> -c| --command <execution-command> -a| --arch| -architecture <architecture>" )
    parser.add_option("-o", "--output", dest="output_file", help="output file name",  type=str, default='')
    parser.add_option("-c", "--command", dest="command", help="Target command to monitor",type=str ,default='')
    parser.add_option("-a", "--arch", dest="architecture", help="Build architecture",  default='')
    opts, args = parser.parse_args()
    stats_file_name = opts.output_file
    architecture = opts.architecture
    cmmnd = opts.command
    cmmnd_is_string = True

  if not cmmnd:
    cmmnd = argv[1:]

  job = {'exit_code':0, 'command':'true', 'command_is_string':cmmnd_is_string, 'command':cmmnd }
  stop_monitoring = False

  job_thd = Thread(target=run_job, args=(job,))
  mon_thd = Thread(target=monitor, args=(lambda: stop_monitoring, stats_file_name,))
  job_thd.start()
  sleep(1)
  mon_thd.start()
  job_thd.join()
  stop_monitoring = True
  mon_thd.join()
  exit(job['exit_code'])

