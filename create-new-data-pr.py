from __future__ import print_function
from github import Github
from optparse import OptionParser
import repo_config
from os.path import expanduser
from urllib2 import urlopen
import json
#, dirname, abspath, join, exists #remove later

def update_tag_version(current_version=None):
    updated_version = None
    if current_version:
        updated_version=str(int(current_version)+1)
        if len(updated_version) == 1:
            updated_version = '0'+updated_version

    return updated_version

if __name__ == "__main__":

  
  parser = OptionParser(usage="%prog <cms-data-repo> <cms-dist repo> <pull-request-id>")

  parser.add_option("-r", "--data-repo", dest="data_repo", help="Github data repositoy name e.g. cms-data/RecoTauTag-TrainingFiles.",
                    type=str, default=None)
  parser.add_option("-d", "--dist-repo", dest="dist_repo", help="Github dist repositoy name e.g. npcbot/cmsdist.",
                    type=str, default='')
  parser.add_option("-p", "--pull-request", dest="pull_request", help="Pull request number",
                    type=str, default=None)
  opts, args = parser.parse_args()
  

  opts.pull_request = '4'
  opts.dist_repo = 'npcbot/cmsdist'
  opts.data_repo = 'npc-data/PhysicsTools-NanoAOD'

  data_prid = int(opts.pull_request)
  token = None
  with open(repo_config.GH_TOKEN) as secret:
      token = secret.read().strip()

  print(token)
  gh = Github(login_or_token=open(expanduser(repo_config.GH_TOKEN)).read().strip())
  user = gh.get_user()
  print('user is', user.login, 'url is ', user.url)
  data_repo = gh.get_repo(opts.data_repo)
  dist_repo = gh.get_repo(opts.dist_repo)
  data_repo_pr = data_repo.get_pull(data_prid)
  response = urlopen('https://api.github.com/repos/'+opts.data_repo+'/tags')
  print('response code: ', response.getcode())

  #tags = data_repo.get_git_tag()
  last_release_tag = data_repo.get_latest_release().tag_name
  print(last_release_tag)

  comparison = data_repo.compare('master', last_release_tag)
  print(comparison.behind_by)
  create_new_tag = True if comparison.behind_by > 0 else False # last tag and master commit difference
  print(create_new_tag)

  # if the latest tag/release compared with master(base) or the pr(head) branch is behind then make new tag
  if create_new_tag:
      nums_only = last_release_tag.strip('V').split('-')
      first, sec, thrd = tuple(nums_only)
      print(first, sec, thrd)
      # update minor for now
      thrd = update_tag_version(thrd)
      print('minor change: ', thrd)
      new_tag = 'V'+first+'-'+sec+'-'+thrd
      print(new_tag)
      # message should be referencing the PR that triggers this job
      new_rel = data_repo.create_git_release(new_tag, new_tag, 'Details in: '+data_repo_pr.html_url, False, False, 'master')
      print(new_rel.tag_name, new_rel.title)

  #print(data_repo_pr.changed_files)
  # get the tags and compare the last tag time with the pr merge time
  # how to
  last_release_tag = data_repo.get_latest_release().tag_name
  default_cms_dist_branch = 'IB/CMSSW_11_0_X/gcc700'
  repo_tag_pr_branch = 'update-'+opts.data_repo.split('/')[1]+'-to-'+last_release_tag
  print(repo_tag_pr_branch)
  sb = dist_repo.get_branch(default_cms_dist_branch)
  dist_repo.create_git_ref(ref='refs/heads/' + repo_tag_pr_branch, sha=sb.commit.sha)
  
