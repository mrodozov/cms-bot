# A ridicously long mapping for categories. Good enough for now.
from cms_static import GH_CMSDIST_REPO as gh_cmsdist
from cms_static import GH_CMSSW_ORGANIZATION as gh_user
from cms_static import GH_CMSSW_REPO as gh_cmssw
from categories_map import CMSSW_CATEGORIES
from repo_config import CMSBUILD_USER

authors = {}
GITHUB_BLACKLIST_AUTHORS = []
CMSSW_L1 = ["mrodozov", "npcbot"]
APPROVE_BUILD_RELEASE =  list(set([ "mrodozov", "npcbot" ] + CMSSW_L1))
REQUEST_BUILD_RELEASE = APPROVE_BUILD_RELEASE
TRIGGER_PR_TESTS = list(set([ "mrodozov", "npcbot"] + REQUEST_BUILD_RELEASE + [ a for a in authors if authors[a]>10 and not a in GITHUB_BLACKLIST_AUTHORS ]))
PR_HOLD_MANAGERS = [ "mrodozov", "npcbot" ]

COMMON_CATEGORIES = [ "orp", "tests", "code-checks" ]
EXTERNAL_CATEGORIES = [ "externals" ]
EXTERNAL_REPOS = [ "cms-data", "cms-externals", gh_user]

CMSSW_REPOS = [ gh_user+"/"+gh_cmssw ]
CMSDIST_REPOS = [ gh_user+"/"+gh_cmsdist ]
CMSSW_ISSUES_TRACKERS = list(set(CMSSW_L1 + [ "mrodozov", "npcbot" ]))
COMPARISON_MISSING_MAP = [ "mrodozov", "npcbot" ]

CMSSW_L2 = {
  "mrodozov"  : ['fastsim', 'core', 'tests', 'upgrade', 'xpog', 'visualization', 'geometry', 'docs', 'hlt', 'db', 'externals', 'analysis', 'alca', 'pdmv', 'generators', 'daq', 'reconstruction', 'l1', 'dqm', 'simulation', 'operations'],
  CMSBUILD_USER:      ["tests" ]

}

USERS_TO_TRIGGER_HOOKS = set(TRIGGER_PR_TESTS + CMSSW_ISSUES_TRACKERS + list(CMSSW_L2.keys()))
CMS_REPOS = set(CMSDIST_REPOS + CMSSW_REPOS + EXTERNAL_REPOS)
from datetime import datetime
COMMENT_CONVERSION = {}
COMMENT_CONVERSION['mrodozov']={'comments_before': datetime.strptime('2018-07-13','%Y-%m-%d'), 'comments':[('+1', '+upgrade')]}


def external_to_package(repo_fullname):
  org, repo = repo_fullname.split("/",1)
  if org == "npc-data":
    return repo.replace('-','/')
  return ''
