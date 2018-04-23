#!/usr/bin/env python
import os, sys, glob, re, json
from commands import getstatusoutput
from multiprocessing import cpu_count
from time import sleep, time
from json import loads, dump
from copy import deepcopy
import threading
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CMS_BOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0,CMS_BOT_DIR)
sys.path.insert(0,SCRIPT_DIR)
from RelValArgs import GetMatrixOptions, FixWFArgs
from es_utils import es_krb_query_exe, format, es_workflow_stats

def createJob(workflow, cmssw_ver, arch):
  workflow_args = FixWFArgs(cmssw_ver, arch, workflow, GetMatrixOptions(cmssw_ver, arch))
  cmd = format("rm -rf %(workflow)s %(workflow)s_*; mkdir %(workflow)s; cd %(workflow)s; PATH=%(das_utils)s:$PATH runTheMatrix.py --maxSteps=0 -l %(workflow)s %(workflow_args)s",workflow=workflow,workflow_args=workflow_args, das_utils=CMS_BOT_DIR+"/das-utils")
  print "Running ",cmd
  e, o = getstatusoutput(cmd)
  if e: print "ERROR:%s:%s" % (workflow, o)
  try:
    workflow_dir = glob.glob(format("%(workflow)s/%(workflow)s_*", workflow=workflow))[0]
    getstatusoutput(format("mv %(workflow)s/runall-report-step123-.log %(workflow_dir)s/workflow.log; touch %(workflow_dir)s/cmdLog; mv %(workflow_dir)s .; rm -rf %(workflow)s", workflow=workflow, workflow_dir=workflow_dir))
    print "Commands for workflow %s generated" % workflow
  except Exception, e:
    print "ERROR: Creating workflow job:",workflow,str(e)
    getstatusoutput("rm -rf %s %s_*" % (workflow,workflow))

pyRunDir=os.path.join(os.environ["CMSSW_BASE"],"pyRelval")
getstatusoutput("rm -rf %s; mkdir -p %s" % (pyRunDir, pyRunDir))
os.chdir(pyRunDir)

cmssw_ver = os.environ["CMSSW_VERSION"]
arch = os.environ["SCRAM_ARCH"]
#Run runTheMatrix with maxStep=0
thrds=[]
jobs=cpu_count()
wf_query=""
print "Creating jobs (%s) ...." % jobs
for wf in sys.argv[1].split(","):
  wf_query+=" OR workflow:"+wf
  while len(thrds)>=jobs:
    sleep(1)
    thrds = [ t for t in thrds if t.is_alive() ]
  t = threading.Thread(target=createJob, args=(wf, cmssw_ver, arch))
  thrds.append(t)
  t.start()
for t in thrds: t.join()

#Get Workflow stats from ES
print "Getting Workflow stats from ES....."
stats = {}
release_cycle=(cmssw_ver.split("_X_")[0]+"_X").lower()
st = 1000*int(time()-(86400*10))
et = 1000*int(time())
es_q = format('exit_code:0 AND release:/%(release_cycle)s.*/ AND architecture:/%(architecture)s.*/ AND (%(workflows)s)', release_cycle=release_cycle, architecture=arch, workflows=wf_query[4:])

while True:
  
  stats = es_krb_query_exe(index='cmssdt-relvals_stats_summary*', query=es_q, start_time=st, end_time=et)
  if (not 'hits' in stats) or (not 'hits' in stats['hits']) or (not stats['hits']['hits']):
    xrelease_cycle = "_".join(cmssw_ver.split("_",4)[0:3])+"_X"
    if xrelease_cycle!=release_cycle:
      release_cycle=xrelease_cycle
      print "Retry: Setting release cycle to ",release_cycle
      continue
  break

wf_stats = es_workflow_stats(stats)

#Create Jobs
print "Creating jobs.json file ...."
jobs = {}
jobs["final_job"] = "echo All Done"
jobs["final_per_group"] = {"command": SCRIPT_DIR+"/workflow_final.py %(jobs_results)s", "cpu": 10,  "rss": 10*1024*1024, "time" : 30}
jobs["env"]={}
jobs["jobs"]=[]
e , o = getstatusoutput ("find . -name workflow.log -type f | sed 's|^./||'")
for cmds_log in o.split("\n"):
  cmds = os.path.join(os.path.dirname(cmds_log),"wf_steps.txt")
  wf = cmds.split("_")[0]
  group ={"name": wf, "commands":[]}
  if os.path.exists(cmds):
    e, o = getstatusoutput ("cat %s | grep ^step" % cmds)
    for c in o.split("\n"):
      job = {"cpu" : 300, "rss" : 4.5*1024*1024*1024, "time" : 120, "command" : re.sub("\s*;\s*$","",c.split(":",1)[-1])}
      step = c.split(":")[0]
      if (wf in wf_stats) and (step in wf_stats[wf]):
        job["time"] = wf_stats[wf][step]["time"]
        for x in ["cpu", "rss"]:
          job[x] = wf_stats[wf][step][x]
          for t in [x+"_avg", x+"_max"]: job[t] = wf_stats[wf][step][t]
      group["commands"].append(job)
  jobs["jobs"].append(group)
dump(jobs, open("jobs.json","w"), sort_keys=True,indent=2)
