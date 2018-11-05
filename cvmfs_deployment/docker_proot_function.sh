dockerrun()
{
  case "${SCRAM_ARCH}" in
    slc6_amd64_* )
      ARGS="cd ${INSTALL_DIR}; $@"
      docker run --net=host --rm -t -v /etc/passwd:/etc/passwd -v /etc/group:/etc/group -e INSTALL_DIR=${INSTALL_DIR} -e SCRAM_ARCH=${SCRAM_ARCH} -e x=${x} -v /tmp:/tmp -v ${INSTALL_DIR}:${INSTALL_DIR} -u $(whoami) cmssw/slc6-installer:latest sh -c "${ARGS}"
      ;;
    slc7_amd64_* )
      ARGS="cd ${INSTALL_DIR}; $@"
      docker run --net=host --rm -t -v /etc/passwd:/etc/passwd -v /etc/group:/etc/group -e -e INSTALL_DIR=${INSTALL_DIR} -e SCRAM_ARCH=${SCRAM_ARCH} -e x=${x} -v /tmp:/tmp -v ${INSTALL_DIR}:${INSTALL_DIR} -u $(whoami) cmssw/slc7-installer:latest sh -c "${ARGS}"
      ;;
    slc7_aarch64_* )
      ARGS="export INSTALL_DIR=${INSTALL_DIR}; export INSTALL_DIR=${INSTALL_DIR}; export SCRAM_ARCH=${SCRAM_ARCH}; export x=${x}; cd ${INSTALL_DIR}; $@"
      $PROOTDIR/proot -R $PROOTDIR/centos-7.2.1511-aarch64-rootfs -b /tmp:tmp -b /build:/build -b /cvmfs:/cvmfs -w ${INSTALL_DIR} -q "$PROOTDIR/qemu-aarch64 -cpu cortex-a57" sh -c "${ARGS}"
      ;;
    fc24_ppc64le_* )
      ARGS="export INSTALL_DIR=${INSTALL_DIR}; export INSTALL_DIR=${INSTALL_DIR}; export SCRAM_ARCH=${SCRAM_ARCH}; export x=${x}; cd ${INSTALL_DIR}; $@"
      $PROOTDIR/proot -R $PROOTDIR/fedora-24-ppc64le-rootfs -b /tmp:/tmp -b /build:/build -b /cvmfs:/cvmfs -w ${INSTALL_DIR} -q "$PROOTDIR/qemu-ppc64le -cpu POWER8" sh -c "${ARGS}"
      ;;
    slc7_ppc64le_* )
      ARGS="export INSTALL_DIR=${INSTALL_DIR}; export INSTALL_DIR=${INSTALL_DIR}; export SCRAM_ARCH=${SCRAM_ARCH}; export x=${x}; cd ${INSTALL_DIR}; $@"
      $PROOTDIR/proot -R $PROOTDIR/centos-7.2.1511-ppc64le-rootfs -b /tmp:/tmp -b /build:/build -b /cvmfs:/cvmfs -w ${INSTALL_DIR} -q "$PROOTDIR/qemu-ppc64le -cpu POWER8" sh -c "${ARGS}"
      ;;
    * )
      eval $@
      ;;
  esac
}
