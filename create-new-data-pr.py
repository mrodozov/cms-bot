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
  #token = None
  #with open(repo_config.GH_TOKEN) as secret:
  #    token = secret.read().strip()

  #print(token)
  gh = Github(login_or_token=open(expanduser(repo_config.GH_TOKEN)).read().strip())
  #user = gh.get_user()
  #print('user is', user.login, 'url is ', user.url)
  data_repo = gh.get_repo(opts.data_repo)
  dist_repo = gh.get_repo(opts.dist_repo)
  data_repo_pr = data_repo.get_pull(data_prid)
  #response = urlopen('https://api.github.com/repos/'+opts.data_repo+'/tags')
  #print('response code: ', response.getcode())
  #tags = data_repo.get_git_tag()
  last_release_tag = data_repo.get_latest_release().tag_name
  print(last_release_tag)

  comparison = data_repo.compare('master', last_release_tag)
  print(comparison.behind_by)
  create_new_tag = True if comparison.behind_by > 0 else False # last tag and master commit difference
  print(create_new_tag)

  # if the latest tag/release compared with master(base) or the pr(head) branch is behind then make new tag
  new_tag = last_release_tag # in case
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
  default_cms_dist_branch = 'IB/CMSSW_11_0_X/gcc700' # give it as and argument to the script, maybe
  repo_name_only = opts.data_repo.split('/')[1]
  repo_tag_pr_branch = 'update-'+repo_name_only+'-to-'+last_release_tag
  print(repo_tag_pr_branch)
  sb = dist_repo.get_branch(default_cms_dist_branch)

  dest_branch = None
  try:
      dist_repo.create_git_ref(ref='refs/heads/' + repo_tag_pr_branch, sha=sb.commit.sha)
      dest_branch = dist_repo.get_branch(repo_tag_pr_branch)
  except Exception as e:
      print(str(e))
      dest_branch = dist_repo.get_branch(repo_tag_pr_branch)
      print('Branch exists')
  print(dest_branch.name)

  # file with tags on the default branch
  cmsswdatafile = "data/cmsswdata.txt"
  content_file = dist_repo.get_contents(cmsswdatafile, repo_tag_pr_branch)
  cmsswdatafile_raw = content_file.decoded_content
  # remove the existing line no matter where it is and put the new line right under default

  new_content = ''
  #see if the tag is the same in the file content, meaning it's already being updated on cmsdist
  #if cmsswdatafile_raw.find(repo_name_only+'='+new_tag):

  count = 0 # omit first line linebreaker
  for line in cmsswdatafile_raw.splitlines():
      updated_line = None
      if '[default]' in line:
          updated_line = '\n'+line+'\n'+repo_name_only+'='+new_tag+''
      elif repo_name_only in line:
          updated_line = ''
      else:
          if count > 0:
              updated_line = '\n'+line
          else:
              updated_line = line
      count=count+1
      new_content = new_content+updated_line
      print('old line\n', line)
      print('new line\n', updated_line)
  print(cmsswdatafile_raw)
  print('updated content')
  print(new_content)

  some_weird_object = dist_repo.update_file(content_file.path, 'Update tag for '+repo_name_only+' to '+new_tag, new_content,
                        content_file.sha, branch=repo_tag_pr_branch)
  #print(some_weird_object)
  change_tag_pull_request = dist_repo.create_pull('Update tag for '+repo_name_only+' to '+new_tag,
                                   'Move '+repo_name_only+' data to new tag, see \n'
                                                  +data_repo_pr.html_url +'\n'
                                                  +' and \n' +data_repo.get_latest_release().html_url +'\n'
                                   , base=default_cms_dist_branch, head=repo_tag_pr_branch,
                                   maintainer_can_modify=True)
  # push with prints, remove them later











