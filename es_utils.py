#!/usr/bin/env python
import sys, urllib2, json, requests, urllib3
from datetime import datetime
from time import time
from os.path import exists
from os import getenv
from requests_kerberos import HTTPKerberosAuth, REQUIRED
#NOTE: requests_kerberos IS NOT !!! part of requests. It brings requests as requrement and not only
#Function to store data in elasticsearch

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def resend_payload(hit, passwd_file="/data/secrets/github_hook_secret_cmsbot"):
  return send_payload(hit["_index"], hit["_type"], hit["_id"],json.dumps(hit["_source"]),passwd_file)

def es_get_passwd(passwd_file=None):
  for psfile in [passwd_file, getenv("CMS_ES_SECRET_FILE",None), "/data/secrets/cmssdt-es-secret", "/build/secrets/cmssdt-es-secret", "/var/lib/jenkins/secrets/cmssdt-es-secret", "/data/secrets/github_hook_secret_cmsbot"]:
    if not psfile: continue
    if exists(psfile):
      passwd_file=psfile
      break
  try:
    return open(passwd_file,'r').read().strip()
  except Exception as e:
    print "Couldn't read the secrets file" , str(e)
    return ""

def send_payload_new(index, document, id, payload, es_server, passwd_file=None):
  index = 'cmssdt-' + index
  passwd=es_get_passwd(passwd_file)
  if not passwd: return False

  url = "https://%s/%s/%s/" % (es_server,index,document)
  if id: url = url+id
  passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
  passman.add_password(None,url, 'cmssdt', passwd)
  auth_handler = urllib2.HTTPBasicAuthHandler(passman)
  opener = urllib2.build_opener(auth_handler)
  try:
    urllib2.install_opener(opener)
    content = urllib2.urlopen(url,payload)
  except Exception as e:
    print "ERROR:",url,str(e)
    return False
  print "OK ",index
  return True

def send_payload_old(index,document,id,payload,passwd_file=None):
  passwd=es_get_passwd(passwd_file)
  if not passwd: return False

  url = "http://%s/%s/%s/" % ('cmses-master02.cern.ch:9200', index, document)
  if id: url = url+id
  passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
  passman.add_password(None,url, 'elasticsearch', passwd)
  auth_handler = urllib2.HTTPBasicAuthHandler(passman)
  opener = urllib2.build_opener(auth_handler)
  try:
    urllib2.install_opener(opener)
    content = urllib2.urlopen(url,payload)
  except Exception as e:
    print "ERROR: ",url, str(e)
    return False
  print "OK ",index
  return True

def delete_hit(hit,passwd_file=None):
  passwd=es_get_passwd(passwd_file)
  if not passwd: return False

  url = "http://%s/%s/%s/%s" % ('cmses-master02.cern.ch:9200',hit["_index"], hit["_type"], hit["_id"])
  passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
  passman.add_password(None,url, 'elasticsearch', passwd)
  auth_handler = urllib2.HTTPBasicAuthHandler(passman)
  opener = urllib2.build_opener(auth_handler)
  try:
    urllib2.install_opener(opener)
    request = urllib2.Request(url)
    request.get_method = lambda: 'DELETE'
    content = urllib2.urlopen(request)
  except Exception as e:
    print "ERROR: ",url, str(e)
    return False
  print "DELETE:",hit["_id"]
  return True

def send_payload(index,document,id,payload,passwd_file="/data/secrets/github_hook_secret_cmsbot"):
  send_payload_new(index,document,id,payload,'es-cmssdt.cern.ch:9203')
  return send_payload_old(index,document,id,payload,passwd_file)

def get_payload(url,query):
  passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
  passman.add_password(None,url, 'kibana', 'kibana')
  auth_handler = urllib2.HTTPBasicAuthHandler(passman)
  opener = urllib2.build_opener(auth_handler)
  try:
    urllib2.install_opener(opener)
    content = urllib2.urlopen(url,query)
    return content.read()
  except Exception as e:
    print "Couldn't send data to elastic search" , str(e)
    return ""

'''
class KerberosTicket:
  def __init__(self, service):
    __, krb_context = kerberos.authGSSClientInit(service)
    kerberos.authGSSClientStep(krb_context, "")
    self._krb_context = krb_context
    self.auth_header = ("Negotiate " +
                        kerberos.authGSSClientResponse(krb_context))
  def verify_response(self, auth_header):
    # Handle comma-separated lists of authentication fields
     for field in auth_header.split(","):
      kind, __, details = field.strip().partition(" ")
      if kind.lower() == "negotiate":
        auth_details = details.strip()
        break
      else:
        raise ValueError("Negotiate not found in %s" % auth_header)
      # Finish the Kerberos handshake
      krb_context = self._krb_context
      if krb_context is None:
        raise RuntimeError("Ticket already used for verification")
      self._krb_context = None
      kerberos.authGSSClientClean(krb_context)
'''

def get_payload_kerberos(url, query):
  #short_url = url.split('/')[2]
  #krb = KerberosTicket("HTTP@"+short_url)
  #headers = {"Authorization": krb.auth_header}
  #r = requests.post(url, headers=headers, verify=False, data=query)
  kerb_auth = HTTPKerberosAuth(mutual_authentication=REQUIRED)
  r = requests.post(url, auth=kerb_auth, verify=False, data=query)
  es_data = json.loads(r.text)
  #print es_data
  scroll_url = 'https://es-cmssdt.cern.ch/krb/_search/scroll'

  scroll_size = es_data['hits']['total']
  final_scroll_data = es_data
  #final_scroll_data.append(es_data['hits']['hits'])

  while (scroll_size > 0):
      scroll_id = es_data['_scroll_id']
      scroll_query = {"scroll_id": str(scroll_id), "scroll": "1m"}

      r = requests.post(scroll_url, auth=kerb_auth ,verify=False, data=json.dumps(scroll_query))

      es_data = json.loads(r.text)
      scroll_size = len(es_data['hits']['hits'])
      if (scroll_size > 0):
          final_scroll_data['hits']['hits'].append(es_data['hits']['hits'][0])

  #print json.dumps(final_scroll_data, indent=2, sort_keys=True, separators=(',', ': '))
  final_scroll_data = {'hits':final_scroll_data['hits'],'_shards':final_scroll_data['_shards'],'took':final_scroll_data['took'],'timed_out':final_scroll_data['timed_out']}
  return final_scroll_data

def format(s, **kwds): return s % kwds

def es_query(index,query,start_time,end_time,page_start=0,page_size=100000,timestamp_field="@timestamp",lowercase_expanded_terms='false', es_host='http://cmses-master02.cern.ch:9200'):
  query_url='%s/%s/_search' % (es_host, index)
  query_tmpl = """{
  "query": {
      "filtered": {
        "query":  {"bool": {"should": [{"query_string": {"query": "%(query)s","lowercase_expanded_terms": %(lowercase_expanded_terms)s}}]}},
        "filter": {"bool": {"must":   [{"range": {"%(timestamp_field)s": {"from": %(start_time)s,"to": %(end_time)s}}}]}}
      }
    },
    "from": %(page_start)s,
    "size": %(page_size)s
  }"""
  query_str = format(query_tmpl, query=query,start_time=start_time,end_time=end_time,page_start=page_start,page_size=page_size,timestamp_field=timestamp_field,lowercase_expanded_terms=lowercase_expanded_terms)
  print 'query url is ', query_url
  return json.loads(get_payload(query_url, query_str))

def es_krb_query(index,query,start_time,end_time,page_start=0,page_size=10000,timestamp_field="@timestamp",lowercase_expanded_terms='false', es_host='https://es-cmssdt.cern.ch/krb'):
  query_url='%s/%s/_search?scroll=1m' % (es_host, index)
  # dont lowercase here
  query_tmpl = """{
  "query": {
    "bool": {
      "filter": [
        {
          "range": {
            "%(timestamp_field)s": {
              "gte": %(start_time)s,
              "lt": %(end_time)s
            }
          }
        }
      ],
      "must": {
        "query_string": {
          "query": "%(query)s"
        }
      }
    }
  },
  "from": %(page_start)s,
  "size": %(page_size)s
  }"""

  query_str = format(query_tmpl, query=query, start_time=start_time, end_time=end_time,page_start=page_start,page_size=page_size,timestamp_field=timestamp_field,lowercase_expanded_terms=lowercase_expanded_terms)
  #print 'query url is ', query_url

  return json.loads(get_payload_kerberos(query_url, query_str))

def es_workflow_stats(es_hits,rss='rss_75', cpu='cpu_75'):
  wf_stats = {}
  for h in es_hits['hits']['hits']:
    hit = h["_source"]
    wf = hit["workflow"]
    step = hit["step"]
    if not wf in wf_stats: wf_stats[wf]={}
    if not step in wf_stats[wf]:wf_stats[wf][step]=[]
    wf_stats[wf][step].append([hit['time'], hit[rss], hit[cpu], hit["rss_max"], hit["cpu_max"]])

  for wf in wf_stats:
    for step in wf_stats[wf]:
      hits = wf_stats[wf][step]
      thits = len(hits)
      time_v = int(sum([h[0] for h in hits])/thits)
      rss_v = int(sum([h[1] for h in hits])/thits)
      cpu_v = int(sum([h[2] for h in hits])/thits)
      rss_m = int(sum([h[3] for h in hits])/thits)
      cpu_m = int(sum([h[4] for h in hits])/thits)
      if rss_v<1024: rss_v = rss_m
      if cpu_v<10: cpu_v = cpu_m
      wf_stats[wf][step] = { "time"  : time_v,
                             "rss"   : rss_v,
                             "cpu"   : cpu_v,
                             "rss_max" : rss_m,
                             "cpu_max" : cpu_m,
                             "rss_avg" : int((rss_v+rss_m)/2),
                             "cpu_avg" : int((cpu_v+cpu_m)/2)
                           }
  return wf_stats

'''
query_tmpl = """{
  "query": {
    "regexp":{
      "job_name": "cms-bot"
      }
    },
  "size" : 1
  }"""
get_payload_kerberos("https://es-cmssdt.cern.ch/krb/cmssdt-jenkins/_search", query_tmpl)
'''

if __name__ == "__main__":

  query_url = 'https://es-cmssdt.cern.ch/krb/cmssdt-relvals_stats_summary*/_search?scroll=1m'
  query="""{
  "query": {
    "bool": {
      "filter": [
        {
          "range": {
            "@timestamp": {
              "gte": "1522241504472",
              "lt": "1522327904472"
            }
          }
        }
      ],
      "must": {
        "query_string": {
          "query": "release:/cmssw_10_2_x.*/ AND architecture:/slc6_amd64_gcc630.*/ "
        }
      }
    }
  },
  "from": 0,
  "size": 10000
  }"""

  result = get_payload_kerberos(query_url, query)
  final_data = result

  #for i in final_data:
  #    print i
  print json.dumps(final_data, indent=2, sort_keys=True, separators=(',', ': '))

  #query_string = 'exit_code:0 AND release:CMSSW_10_2_X_2018-04* AND architecture:slc6_amd64_gcc630'
  #st = 1000*int(time()-(86400*10))
  #et = 1000*int(time())

  #result = es_query(index='relvals_stats_*', query=query_string, start_time=st,end_time= et)
  #for i in result:
  #    print i
  #print json.dumps(result, indent=2, sort_keys=True, separators=(',', ': '))

  #query_string = "release:/cmssw_10_2_x.*/ AND architecture:/slc7_amd64_gcc.*/ AND (workflow:2.0) AND exit_code: 0"
  #es_krb_query()
