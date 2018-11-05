#  bootstrap - check if it exists and install if doesn't exist
if [ $(ls -al ${INSTALL_PATH}/${ARCHITECTURE}/external/rpm/*/etc/profile.d/init.sh 2>/dev/null 1>/dev/null ; echo $? ; ) -ne 0 ] ; then
    echo 'boostrap not found, installing'
    wget --tries=5 --waitretry=60 -O ${WORKDIR}/bootstrap.sh http://cmsrep.cern.ch/cmssw/repos/bootstrap.sh
    dockerrun "sh -ex ${WORKDIR}/bootstrap.sh -a ${ARCHITECTURE} -repository ${RPMS_REPO} -path ${WORKDIR} setup"
fi
