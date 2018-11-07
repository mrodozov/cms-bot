#!/bin/bash -ex

#  vars set because some functions are using them
INSTALL_PATH=$1
ARCHITECTURE=$2
RPMS_REPO=$3
PACKAGE_NAME=$4

SCRAM_ARCH=$ARCHITECTURE #  for dockerrun function
PROOT_DIR="${INSTALL_PATH}/proot"  #  or prefixed on cvmfs, doesn't matter

#  get dockerrun function

cd $INSTALL_PATH
source cms-bot/cvmfs_deployment/docker_proot_function.sh
#  proot have to exist, so setup it first if it doesn't. proot is a program if you wonder again what is this thing
sh -ex cms-bot/cvmfs_deployment/install_proot.sh
#  check bootstrap
sh -ex cms-bot/cvmfs_deployment/bootstrap_dir_for_arch.sh $INSTALL_PATH $ARCHITECTURE $PROOT_DIR $RPMS_REPO

#  check how many packages are available
number_of_matches=$(dockerrun "${INSTALL_PATH}/common/cmspkg -a ${ARCHITECTURE} search ${PACKAGE_NAME} | sed -e 's|[ ].*||' | grep -e \"^${PACKAGE_NAME}\$\" | wc -l" | tr -dc '0-9' )
echo "   number of search matches: $number_of_matches"
echo "   lenght of variable: ${#number_of_matches} "

#  package should be only 1, see if not equal to 1. All > 1 is ambiguous
if [[ $number_of_matches == 1 ]] ; then
#  install the package if it's available
    echo '  pkg found, install it'
    pwd
    dockerrun "${INSTALL_PATH}/common/cmspkg -a ${ARCHITECTURE} install -y ${PACKAGE_NAME} -p ${INSTALL_PATH}"
else
#  or, print the package was not found
echo '  pkg not found or more than one found (leading to ambiguity)'
fi