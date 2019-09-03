from cms_static import GH_CMSSW_ORGANIZATION,GH_CMSSW_REPO,CMSBUILD_GH_USER
from os.path import dirname,abspath
GH_TOKEN="~/Desktop/github-token.txt"
GH_TOKEN_READONLY="~/Desktop/github-token.txt"
CONFIG_DIR=dirname(abspath(__file__))
#CMSBUILD_USER=CMSBUILD_GH_USER
CMSBUILD_USER="npcbot"
GH_REPO_ORGANIZATION=GH_CMSSW_ORGANIZATION
CREATE_EXTERNAL_ISSUE=True
JENKINS_SERVER="http://somejenkins.trololo.lo"
IGNORE_ISSUES = {
  GH_CMSSW_ORGANIZATION+"/"+GH_CMSSW_REPO : [12368],
}
