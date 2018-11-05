PROOT_URL="https://cmssdt.cern.ch/SDT/proot/"
PROOTDIR="${INSTALL_PATH}/proot"
if [[ ! -d $PROOTDIR ]] ; then
    mkdir -p $PROOTDIR
    cd $PROOTDIR
    wget -nv -r -nH -nd -np -m -R *.html* $PROOT_URL
    #  make proot and care executable
    chmod +x ${PROOTDIR}/care ${PROOTDIR}/proot  ${PROOTDIR}/qemu*
    for i in `ls | grep bz2`; do
	tar xjf $i ;
	done
fi
