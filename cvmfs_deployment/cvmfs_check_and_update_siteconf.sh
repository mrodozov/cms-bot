#!/bin/sh
# #############################################################################
# cvmfs_update.sh   Simple script to keep a SYNC_DIR area up-to-date with
#                   config files for jobs from the SITECONF repository.
#                   Script aquires a lock to prevent multiple, simultaneous
#                   executions; queries SiteDB for a list of CMS sites; fetches
#                   the commit information from the SITECONF GitLab repository;
#                   removes sites in SYNC_DIR no longer in SiteDB; updates job
#                   config files for sites where the files got updated;
#
#                   Please configure the SYNC_DIR, TMP_AREA (for temporary
#                   files during script execution), AUTH_CRT, AUTH_KEY (pem
#                   files with your cert/key), AUTH_TKN (your token in GitLab),
#                   and EMAIL_ADDR (in case of errors) before execution.
# Created by Stephan Lammel
# Developed by Bockjoo Kim to use it for the cvmfs
# Revision
# versions Description
# 0.1      Original
# 0.2      Add more debug
# 0.3      Use date command to calculate epochs timestamp
# version=0.3
# 
# #############################################################################
SKIP_SITES="T3_US_ANL"
EXC_LOCK=""
TMP_AREA="/tmp/cvmfs_tmp"
ERR_FILE="/tmp/stcnf_$$.err"
EVERY_X_HOUR=4

echo DEBUG TMP_AREA=$TMP_AREA
trap 'exit 1' 1 2 3 15
trap '(/bin/rm -rf ${EXC_LOCK} ${TMP_AREA} ${ERR_FILE}) 1> /dev/null 2>&1' 0

if [ $# -lt 3 ] ; then
   echo ERROR $(basename $0) SYNC_DIR AUTH_TKN EMAIL
   exit 1
fi
SYNC_DIR="$1"        # /cvmfs/cms.cern.ch
AUTH_TKN="$(cat $2)" # private token
EMAIL_ADDR="$3"      # your email
AUTH_CRT="$X509_USER_PROXY"
AUTH_KEY="$X509_USER_PROXY"
echo "[0] SYNC_DIR=$SYNC_DIR"
# #############################################################################



# get cvmfs/stcnf_updt lock:
# --------------------------
echo "[1] Acquiring lock for cvmfs/stcnf_updt"
if [ ! -d /var/tmp/cmssst ]; then
   /bin/rm -f /var/tmp/cvmfs 1>/dev/null 2>&1
   /bin/mkdir /var/tmp/cvmfs 1>/dev/null 2>&1
fi
/bin/ln -s $$ /var/tmp/cvmfs/stcnf_updt.lock
if [ $? -ne 0 ]; then
   # locking failed, get lock information
   LKINFO=`/bin/ls -il /var/tmp/cvmfs/stcnf_updt.lock 2>/dev/null`
   LKFID=`echo ${LKINFO} | /usr/bin/awk '{print $1; exit}' 2>/dev/null`
   LKPID=`echo ${LKINFO} | /usr/bin/awk '{print $NF;exit}' 2>/dev/null`
   # check process holding lock is still active
   /bin/ps -fp ${LKPID} 1>/dev/null 2>&1
   if [ $? -eq 0 ]; then
      echo "   active process ${LKPID} holds lock, exiting"
      exit 1
   fi
   echo "   removing leftover lock: ${LKINFO}"
   /usr/bin/find /var/tmp/cvmfs -inum ${LKFID} -exec /bin/rm -f {} \;
   LKPID=""
   LKFID=""
   LKINFO=""
   #
   /bin/ln -s $$ /var/tmp/cvmfs/stcnf_updt.lock
   if [ $? -ne 0 ]; then
      echo "   failed to acquire lock, exiting"
      exit 1
   fi
fi
#
# double check we have the lock
LKPID=`(/bin/ls -l /var/tmp/cvmfs/stcnf_updt.lock | /usr/bin/awk '{if($(NF-1)=="->")print $NF;else print "";exit}') 2>/dev/null`
if [ "${LKPID}" != "$$" ]; then
   echo "   lost lock to process ${LKPID}, exiting"
   exit 1
fi
LKPID=""
EXC_LOCK="/var/tmp/cvmfs/stcnf_updt.lock"
# #############################################################################



/bin/rm -f ${ERR_FILE} 1>/dev/null 2>&1
#
/bin/rm -rf ${TMP_AREA} 1>/dev/null 2>&1
/bin/mkdir ${TMP_AREA} 1>${ERR_FILE} 2>&1
RC=$?
if [ ${RC} -ne 0 ]; then
   MSG="failed to create TMP_AREA, mkdir=${RC}"
   /bin/cat ${ERR_FILE}
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
   fi
   exit ${RC}
fi
/bin/rm -f ${ERR_FILE} 1>/dev/null 2>&1
#
if [ ! -d ${SYNC_DIR} ]; then
   #/bin/mkdir ${SYNC_DIR} 1>${ERR_FILE} 2>&1
   echo DEBUG doing /bin/mkdir -p ${SYNC_DIR} at $(pwd)
   /bin/mkdir -p ${SYNC_DIR} 1>${ERR_FILE} 2>&1
   RC=$?
   if [ ${RC} -ne 0 ]; then
      MSG="failed to create SYNC_DIR, mkdir=${RC}"
      /bin/cat ${ERR_FILE}
      echo "   ${MSG}"
      if [ ! -t 0 ]; then
         /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
      fi
      exit ${RC}
   fi
fi
/bin/rm -f ${ERR_FILE} 1>/dev/null 2>&1
if [ ! -d ${SYNC_DIR}/SITECONF ]; then
   /bin/mkdir ${SYNC_DIR}/SITECONF 1>${ERR_FILE} 2>&1
   RC=$?
   if [ ${RC} -ne 0 ]; then
      MSG="failed to create SYNC_DIR/SITECONF, mkdir=${RC}"
      /bin/cat ${ERR_FILE}
      echo "   ${MSG}"
      if [ ! -t 0 ]; then
         /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
      fi
      exit ${RC}
   fi
fi
/bin/rm -f ${ERR_FILE} 1>/dev/null 2>&1
# #############################################################################



# extract awk script:
# ===================
/bin/rm -f ${TMP_AREA}/sitedb.awk 1> /dev/null 2>&1
/bin/cat 1>${TMP_AREA}/sitedb.awk 2>${ERR_FILE} << 'EOF_sitedb.awk'
#!/bin/awk -f
BEGIN{brck=0}
{
   todo=$0
   while(length(todo)>=1){
      ob=index(todo,"[")
      cb=index(todo,"]")
      if((ob!=0)&&((cb==0)||(ob<cb))){
         brck+=1
         if(brck==2)line=substr(todo,ob+1)
         todo=substr(todo,ob+1)
      }else{
         if(cb!=0){
            todo=substr(todo,cb+1);
            if(brck==2){
               len=length(line)-length(todo)-1
               line=substr(line,0,len)
               nk=split(line,a,",")
               if(a[1]=="\"cms\""){
                  gsub(" ","",a[3]);gsub("\"","",a[3])
                  print a[3]
               }
            }
            brck-=1
         }else{
            break
         }
      }
   }
}
EOF_sitedb.awk
RC=$?
if [ ${RC} -ne 0 ]; then
   MSG="failed to write sitedb.awk, cat=${RC}"
   /bin/cat ${ERR_FILE}
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
   fi
   exit ${RC}
fi
/bin/rm ${ERR_FILE} 1>/dev/null 2>&1
#
/bin/rm -f ${TMP_AREA}/gitlab.awk 1> /dev/null 2>&1
/bin/cat 1>${TMP_AREA}/gitlab.awk 2>${ERR_FILE} << 'EOF_gitlab.awk'
#!/bin/awk -f
BEGIN{now=systime();brcs=0}
{
   todo=$0
   while(length(todo)>=1){
      ob=index(todo,"{")
      cb=index(todo,"}")
      if((ob!=0)&&((cb==0)||(ob<cb))){
         brcs+=1
         if(brcs==1){site="";last=now;keys=substr(todo,ob+1);sobj=0}
         if(brcs==2)sobj=ob
         todo=substr(todo,ob+1)
      }else{
         if(cb!=0){
            todo=substr(todo,cb+1);
            if(brcs==1){
               len=length(keys)-length(todo)-1
               if(sobj==0){
                  keys=substr(keys,0,len)
               }else{
                  key1=substr(keys,0,sobj)
                  key2=substr(keys,eobj,len-eobj+1)
                  keys=(key1 key2)
               }
               nk=split(keys,a,",")
               for(i=nk;i>0;i-=1){
                  if(index(a[i],"\"name\":")>0){
                     site=substr(a[i],8)
                     gsub("\"","",site)
                  }
                  if(index(a[i],"\"last_activity_at\":")>0){
                     ts=substr(a[i],21,19)
                     ts2=substr(a[i],21,19)
                     gsub("-"," ",ts);gsub("T"," ",ts);gsub(":"," ",ts)
                     gsub("-","",ts2);gsub("T"," ",ts2)
                     tzn=substr(a[i],44,3)
                     last=mktime(ts)-3600*tzn
                  }
               }
               if(site!="")printf "%s:%s:%s\n",site,last,ts2
            }
            if(brcs==2)eobj=length(keys)-length(todo)
            brcs-=1
         }else{
            break
         }
      }
   }
}
EOF_gitlab.awk
RC=$?
if [ ${RC} -ne 0 ]; then
   MSG="failed to write gitlab.awk, cat=${RC}"
   /bin/cat ${ERR_FILE}
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
   fi
   exit ${RC}
fi
/bin/rm ${ERR_FILE} 1>/dev/null 2>&1
# #############################################################################



# get list of CMS sites:
# ======================
echo "[2] Fetching list of CMS sites..."
SITES_URL="https://cmsweb.cern.ch/sitedb/data/prod/site-names"
/bin/rm -f ${TMP_AREA}/sitedb.json 1>/dev/null 2>&1
#/usr/bin/wget --certificate=${AUTH_CRT} --private-key=${AUTH_KEY} -O ${TMP_AREA}/sitedb.json ${SITES_URL} 1>${ERR_FILE} 2>&1
/usr/bin/curl -s -S --cert ${AUTH_CRT} --key ${AUTH_CRT} --cacert ${AUTH_CRT} --capath /etc/grid-security/certificates -o ${TMP_AREA}/sitedb.json -X GET "${SITES_URL}" 1>${ERR_FILE} 2>&1
RC=$?
if [ ${RC} -ne 0 ]; then
   MSG="failed to query SiteDB to get site-names, curl=${RC}"
   /bin/cat ${ERR_FILE}
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
   fi
   exit ${RC}
fi
/bin/rm ${ERR_FILE} 1>/dev/null 2>&1
#
# make list of CMS site names:
echo DEBUG content of sitedb.json
echo cat ${TMP_AREA}/sitedb.json 
echo DEBUG end of content of sitedb.json
/bin/rm -f ${TMP_AREA}/sitedb.list
/usr/bin/awk -f ${TMP_AREA}/sitedb.awk ${TMP_AREA}/sitedb.json 1>${TMP_AREA}/sitedb.list
/bin/rm ${TMP_AREA}/sitedb.json
echo DEBUG ${TMP_AREA}/sitedb.list
cat ${TMP_AREA}/sitedb.list
echo DEBUG end of ${TMP_AREA}/sitedb.list
#
# sanity check of SiteDB sites:
if [ `/usr/bin/awk 'BEGIN{nl=0}{nl+=1}END{print nl}' ${TMP_AREA}/sitedb.list 2>/dev/null` -lt 100 ]; then
   MSG="sanity check of SiteDB sites failed, exiting"
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      echo "${SDB_LIST}" | /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR}
   fi
   exit 1
fi
if [ `(/bin/grep '^T0_' ${TMP_AREA}/sitedb.list | /usr/bin/wc -l) 2>/dev/null` -lt 1 ]; then
   MSG="sanity check of SiteDB Tier-0 count failed, exiting"
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      echo "${SDB_LIST}" | /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR}
   fi
   exit 1
fi
if [ `(/bin/grep '^T1_' ${TMP_AREA}/sitedb.list | /usr/bin/wc -l) 2>/dev/null` -lt 5 ]; then
   MSG="sanity check of SiteDB Tier-1 count failed, exiting"
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      echo "${SDB_LIST}" | /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR}
   fi
   exit 1
fi
if [ `(/bin/grep '^T2_' ${TMP_AREA}/sitedb.list | /usr/bin/wc -l) 2>/dev/null` -lt 40 ]; then
   MSG="sanity check of SiteDB Tier-2 count failed, exiting"
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      echo "${SDB_LIST}" | /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR}
   fi
   exit 1
fi
if [ `(/bin/grep '^T3_' ${TMP_AREA}/sitedb.list | /usr/bin/wc -l) 2>/dev/null` -lt 50 ]; then
   MSG="sanity check of SiteDB Tier-3 count failed, exiting"
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      echo "${SDB_LIST}" | /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR}
   fi
   exit 1
fi
# #############################################################################



# get list of GitLab projects (CMS sites) with last update time:
# ==============================================================
echo "[3] Fetching list of GitLab projects/sites..."
/bin/cp /dev/null ${ERR_FILE} 1>/dev/null 2>&1
SUCC=0
FAIL=0
for PAGE in 1 2 3 4 5 6 7 8 9; do
   /usr/bin/wget --header="PRIVATE-TOKEN: ${AUTH_TKN}" --read-timeout=90 -O ${TMP_AREA}/gitlab_${PAGE}.json 'https://gitlab.cern.ch/api/v4/groups/SITECONF/projects?per_page=100&page='${PAGE} 1>>${ERR_FILE} 2>&1
   RC=$?
   echo DEBUG gitlab page:
   #cat ${TMP_AREA}/gitlab_${PAGE}.json
   if [ ${RC} -eq 0 ]; then
      SUCC=1
      /bin/grep name ${TMP_AREA}/gitlab_${PAGE}.json 1>/dev/null 2>&1
      if [ $? -ne 0 ]; then
         break
      fi
      echo DEBUG gitlab_${PAGE}.json PAGE=$PAGE OK
   else
      FAIL=1
      MSG="failed to query GitLab projects, page ${PAGE}, wget=${RC}"
      echo "   ${MSG}"
      if [ ! -t 0 ]; then
         echo "${MSG}" >> ${ERR_FILE}
         echo "" >> ${ERR_FILE}
      fi
      echo DEBUG gitlab_${PAGE}.json PAGE=$PAGE OK
   fi
done
if [ ${FAIL} -ne 0 ]; then
   MSG="failed to query GitLab projects"
   echo ""
   /bin/cat ${ERR_FILE}
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
   fi
fi
if [ ${SUCC} -eq 0 ]; then
   exit 1
fi
/bin/rm ${ERR_FILE} 1>/dev/null 2>&1
#
echo DEBUG ${TMP_AREA}/.timestamp
cat ${TMP_AREA}/.timestamp

echo DEBUG /bin/rm -f ${TMP_AREA}/.timestamp
/bin/rm -f ${TMP_AREA}/.timestamp
#echo DEBUG ${TMP_AREA}/gitlab_\*.json
#for f in ${TMP_AREA}/gitlab_\*.json ; do
#   echo DEBUG $f
#done
for f in in ${TMP_AREA}/gitlab_[0-9]*.json ; do
   echo DEBUG cat $f
   cat $f
done
#echo DEBUG /usr/bin/awk -f ${TMP_AREA}/gitlab.awk ${TMP_AREA}/gitlab_\*.json
#/usr/bin/awk -f ${TMP_AREA}/gitlab.awk ${TMP_AREA}/gitlab_*.json 1>${TMP_AREA}/.timestamp
#echo DEBUG checking ${TMP_AREA}/gitlab.awk
#cat  ${TMP_AREA}/gitlab.awk
if [ ] ; then
   /usr/bin/awk -f ${TMP_AREA}/gitlab.awk ${TMP_AREA}/gitlab_*.json 1>${TMP_AREA}/.timestamp1
else
   #for f in ${TMP_AREA}/gitlab_*.json ; do
   #   /bin/cp $f $HOME/$(basename $f).$(date +%Y%m%d)
   #done
   #sed "s#SITECONF/T#\nSITECONF/T#g" ${TMP_AREA}/gitlab_[0-9]*.json | grep last_activity_at | \
   #while read line ; do 
   #   site_last_activity=$(echo $line | sed 's#,#\n#g' | grep "SITECONF/T\|last_activity_at")
   #   site=$(echo $site_last_activity | cut -d/ -f2 | cut -d\" -f1)
   #   timestamp=$(echo $site_last_activity | cut -d: -f2- | cut -d. -f1)\"
   #   timestamp=$(date -d "$(echo $timestamp | sed 's#\"##g')" +%s)
   #   echo $site:$timestamp | sed 's#"##g'
   #done > ${TMP_AREA}/.timestamp # | grep "T3_US_UMiss\|UMISS\|Florida\|T3_US_TAMU\|T0_CH_CERN\|T2_CH_CERN\|T3_KR_KISTI\|T3_US_Colorado\|T2_FR_GRIF_LLR\|T3_BY_NCPHEP\|T3_IT_Trieste\|T3_KR_UOS\|T3_US_UCR\|T3_CH_Volunteer\|T3_US_NotreDame\|T2_KR_KISTI\|T3_US_UMD\|T3_US_Rutgers\|T2_BE_UCL\|T3_FR_IPNL\|T3_CH_PSI\|T3_US_OSG\|T3_US_TACC\|T2_US_MIT\|T2_IT_Pisa\|T2_FI_HIP" > ${TMP_AREA}/.timestamp
   sed 's#"name":"T#\n"name":"T#g' ${TMP_AREA}/gitlab_[0-9]*.json | grep last_activity_at | \
   while read line ; do 
      site_last_activity=$(echo $line | sed 's#,#^\n#g' | grep "\"name\":\"T\|last_activity_at")
      site=$(echo $site_last_activity | cut -d\^ -f1 | cut -d: -f2 | sed 's#"##g')
      timestamp=$(echo $site_last_activity | cut -d\^ -f2 | cut -d: -f2- | cut -d. -f1 | sed 's#"##g')
      timestamp=$(date -d "$timestamp" +%s)
      echo $site:$timestamp
   done > ${TMP_AREA}/.timestamp
fi

if [ ] ; then
echo DEBUG checking ${TMP_AREA}/.timestamp1
cat ${TMP_AREA}/.timestamp1
echo DEBUG checking ${TMP_AREA}/.timestamp2
cat ${TMP_AREA}/.timestamp2
while read line ; do
   site=$(echo $line | cut -d: -f1)
   t1=$(echo $line | cut -d: -f2)
   t2=$(echo $line | cut -d: -f3-)
   #[ "x$site" == "xT2_CH_CERN_HLT" ] && { t2cern=$(expr $(date --date "$t2" +%s) + 3600) ; echo ${site}:$t2cern ; continue ; }
   echo DEBUG t1=$t1 t2=$t2 t2 should be in time format
   echo ${site}:$(date --date "$t2" +%s)
done < ${TMP_AREA}/.timestamp1

while read line ; do
   site=$(echo $line | cut -d: -f1)
   t1=$(echo $line | cut -d: -f2)
   t2=$(echo $line | cut -d: -f3-)
   #[ "x$site" == "xT2_CH_CERN_HLT" ] && { t2cern=$(expr $(date --date "$t2" +%s) + 3600) ; echo ${site}:$t2cern ; continue ; }
   echo ${site}:$(date --date "$t2" +%s)
done < ${TMP_AREA}/.timestamp1 > ${TMP_AREA}/.timestamp
fi

#cp ${TMP_AREA}/.timestamp2 ${TMP_AREA}/.timestamp
echo DEBUG timestamp "(should not be empty)"
cat ${TMP_AREA}/.timestamp
#echo DEBUG timestamp
#cat ${TMP_AREA}/.timestamp

#echo DEBUG content of timestamp at $(date)
#ls -al ${TMP_AREA}/.timestamp

#cat ${TMP_AREA}/.timestamp
#cp ${TMP_AREA}/gitlab_*.json $HOME/
#cp ${TMP_AREA}/gitlab.awk $HOME/

#echo DEBUG /bin/rm ${TMP_AREA}/gitlab_\*.json
/bin/rm ${TMP_AREA}/gitlab_*.json
# #############################################################################



echo "[4] loop over SYNC_DIR ${SYNC_DIR} CMS sites and remove sites no longer in SiteDB..."
# loop over SYNC_DIR CMS sites and remove sites no longer in SiteDB:
# ==================================================================
/bin/cp /dev/null ${ERR_FILE} 1>/dev/null 2>&1
FAIL=0
SYNC_LIST=`(cd ${SYNC_DIR}/SITECONF; /bin/ls -d1 T?_??_*) 2>/dev/null`
for SITE in ${SYNC_LIST}; do
   echo DEBUG site=$SITE checking /bin/grep "^${SITE}\$" ${TMP_AREA}/sitedb.list
   /bin/grep "^${SITE}\$" ${TMP_AREA}/sitedb.list 1>/dev/null 2>&1
   if [ $? -ne 0 ]; then
      echo "Site \"${SITE}\" no longer in SiteDB, removing site area"
      /bin/rm -rf ${SYNC_DIR}/SITECONF/${SITE} 1>>${ERR_FILE} 2>&1
      RC=$?
      if [ ${RC} -ne 0 ]; then
         FAIL=1
         MSG="failed to remove area of ${SITE} not in SiteDB, rm=${RC}"
         echo "   ${MSG}"
         if [ ! -t 0 ]; then
            echo "${MSG}" >> ${ERR_FILE}
            echo "" >> ${ERR_FILE}
         fi
      fi
      /bin/rm ${ERR_FILE} 1>/dev/null 2>&1
      #
      /bin/touch ${SYNC_DIR}/SITECONF/.timestamp
      /bin/sed -i "/^${SITE}:/d" ${SYNC_DIR}/SITECONF/.timestamp
   fi
done
if [ ${FAIL} -ne 0 ]; then
   MSG="failed to remove areas not in SiteDB"
   echo ""
   /bin/cat ${ERR_FILE}
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
   fi
   exit 1
fi
/bin/rm ${ERR_FILE} 1>/dev/null 2>&1
# #############################################################################



echo "[5] loop over SiteDB sites and update SYNC_DIR as needed"
# loop over SiteDB sites and update SYNC_DIR as needed:
# =====================================================
/bin/cp /dev/null ${ERR_FILE} 1>/dev/null 2>&1
list_sites_updated=""
FAIL=0
isite=0
for SITE in `/bin/cat ${TMP_AREA}/sitedb.list`; do
   isite=$(expr $isite + 1)
   echo DEBUG doing SITE=$SITE
   NEWT=`/usr/bin/awk -F: '{if($1=="'${SITE}'"){print $2}}' ${TMP_AREA}/.timestamp 2>/dev/null`
   if [ -z "${NEWT}" ]; then
      # no repository for this SiteDB site
      echo DEBUG SITE=$SITE no repository for this SiteDB site. Continuing...      
      continue
   fi
   if [ -f ${SYNC_DIR}/SITECONF/.timestamp ]; then
      OLDT=`/usr/bin/awk -F: '{if($1=="'${SITE}'"){print $2}}' ${SYNC_DIR}/SITECONF/.timestamp 2>/dev/null`
      if [ "${NEWT}" = "${OLDT}" ]; then
         # SYNC_DIR up-to-date
         echo DEBUG SITE=$SITE SYNC_DIR up-to-date. Continuing... OLDT=$OLDT NEWT=$NEWT
         #
         # 02APR2018
         # timestamp in https://gitlab.cern.ch/api/v3/groups/SITECONF/projects?per_page=100&page=1
         # is not fine-grained. If the change happens in less than 5 minutes, the timestamp does not change
         # so I am ignoring timestamp-based update every four hour.
         # every four hour all sites that changed are updated
         #
         # continue
         [ $(expr $(date +%H) % $EVERY_X_HOUR) -eq 0 ] || { echo DEBUG "[ $isite ]" SITE=$SITE HOUR=$(date +%H) so ignore timestamp for once ; continue ; } ;
     fi
   fi

   #for site in $SKIP_SITES ; do echo $site ; done | grep -q ^${SITE}$
   #
   # [ $? -eq 0 ] && { echo Warning $SITE in SKIP_SITES list. Will ignore $SITE ; continue ; } ;
   #

   #
   # need to update SITECONF:
   # ------------------------
   echo "[5-1] Updating area of site \"${SITE}\":"
   UPPER=`echo ${SITE} | /usr/bin/tr '[:lower:]' '[:upper:]'`
   /usr/bin/wget --header="PRIVATE-TOKEN: ${AUTH_TKN}" --read-timeout=180 -O ${TMP_AREA}/archive_${SITE}.tgz 'https://gitlab.cern.ch/SITECONF/'${UPPER}'/repository/archive.tar.gz?ref=master' 1>>${ERR_FILE} 2>&1
   RC=$?
   if [ ${RC} -ne 0 ]; then
      /usr/bin/wget --header="PRIVATE-TOKEN: ${AUTH_TKN}" --read-timeout=180 -O ${TMP_AREA}/archive_${SITE}.tgz 'https://gitlab.cern.ch/SITECONF/'${UPPER}'/repository/archive.tar.gz?ref=master' 2>&1 | grep -q "Authorization failed"
      if [ $? -eq 0 ] ; then
         echo Warning: wget Authorization failed with $SITE. This should not have happened
         continue
      fi
      FAIL=1
      MSG="failed to fetch GitLab archive of ${SITE}, wget=${RC}"
      echo "   ${MSG}"
      if [ ! -t 0 ]; then
         echo "${MSG}" >> ${ERR_FILE}
         echo "" >> ${ERR_FILE}
      fi
      continue
   fi
   #
   TAR_DIR=`(/bin/tar -tzf ${TMP_AREA}/archive_${SITE}.tgz | /usr/bin/awk -F/ '{print $1;exit}') 2>/dev/null`
   TAR_LST=`(/bin/tar -tzf ${TMP_AREA}/archive_${SITE}.tgz | /usr/bin/awk -F/ '{if((($2=="JobConfig")&&(match($3,".*site-local-config.*\\.xml$")!=0))||(($2=="JobConfig")&&(match($3,"^cmsset_.*\\.c?sh$")!=0))||(($2=="PhEDEx")&&(match($3,".*storage.*\\.xml$")!=0))||(($2=="Tier0")&&($3=="override_catalog.xml"))||(($2=="GlideinConfig")&&($3=="")))print $0}') 2>/dev/null`
   #
   # 17JUL2018 forget about sites that do not have xml files in the gitlab
   if [ -s ${TMP_AREA}/archive_${SITE}.tgz ] ; then
      tar tzvf ${TMP_AREA}/archive_${SITE}.tgz 2>&1 | grep -q xml
      if [ $? -ne 0 ] ; then
         echo "   Warning: ${TMP_AREA}/archive_${SITE}.tgz does not have config files not extracting tar archive"
         continue
      fi
   fi
   if [ -n "${TAR_LST}" ]; then
      echo "   extracting tar archive"
      (cd ${SYNC_DIR}/SITECONF; /bin/tar -xzf ${TMP_AREA}/archive_${SITE}.tgz ${TAR_LST}) 1>>${ERR_FILE} 2>&1
   else
      /bin/mkdir ${SYNC_DIR}/SITECONF/${TAR_DIR}
      /bin/mkdir ${SYNC_DIR}/SITECONF/${TAR_DIR}/JobConfig
   fi
   RC=$?
   if [ ${RC} -ne 0 ]; then
      FAIL=1
      MSG="failed to extract tar archive of ${SITE}, tar=${RC}"
      echo "   ${MSG}"
      if [ ! -t 0 ]; then
         echo "${MSG}" >> ${ERR_FILE}
         echo "" >> ${ERR_FILE}
         /bin/rm ${TMP_AREA}/archive_${SITE}.tgz
      fi
      continue
   fi
   #[ "$SITE" == "T2_CH_CERN_HLT" ] && cp ${TMP_AREA}/archive_${SITE}.tgz $HOME/
   /bin/rm ${TMP_AREA}/archive_${SITE}.tgz
   #
   # avoid directory file update in case extracted files did not change
   /usr/bin/diff -r ${SYNC_DIR}/SITECONF/${SITE} ${SYNC_DIR}/SITECONF/${TAR_DIR} 1>/dev/null 2>&1
   status=$?
   echo DEBUG status=$status checking /usr/bin/diff -r ${SYNC_DIR}/SITECONF/${SITE} ${SYNC_DIR}/SITECONF/${TAR_DIR}
   /usr/bin/diff -r ${SYNC_DIR}/SITECONF/${SITE} ${SYNC_DIR}/SITECONF/${TAR_DIR}
   if [ "$SITE" == "T2_CH_CERN_HLT" ] ; then
      echo cat ${SYNC_DIR}/SITECONF/${SITE}/JobConfig/site-local-config.xml 
      cat ${SYNC_DIR}/SITECONF/${SITE}/JobConfig/site-local-config.xml 
      echo cat ${SYNC_DIR}/SITECONF/${TAR_DIR}JobConfig/site-local-config.xml 
      cat ${SYNC_DIR}/SITECONF/${TAR_DIR}JobConfig/site-local-config.xml 
   fi
   if [ $status -eq 0 ]; then
      # no file difference, keep old area
      echo "   no change to CVMFS files, keeping old area"
      /bin/rm -rf ${SYNC_DIR}/SITECONF/${TAR_DIR} 1>>${ERR_FILE} 2>&1
      RC=$?
      if [ ${RC} -ne 0 ]; then
         FAIL=1
         MSG="failed to remove new area of ${SITE}, rm=${RC}"
         echo "   ${MSG}"
         if [ ! -t 0 ]; then
            echo "${MSG}" >> ${ERR_FILE}
            echo "" >> ${ERR_FILE}
         fi
      fi
   else
      #
      if [ -e ${SYNC_DIR}/SITECONF/${SITE} ]; then
         echo "   removing old CVMFS area"
         /bin/rm -rf ${SYNC_DIR}/SITECONF/${SITE} 1>>${ERR_FILE} 2>&1
         RC=$?
         if [ ${RC} -ne 0 ]; then
            FAIL=1
            MSG="failed to remove old area of ${SITE}, rm=${RC}"
            echo "   ${MSG}"
            if [ ! -t 0 ]; then
               echo "${MSG}" >> ${ERR_FILE}
               echo "" >> ${ERR_FILE}
               /bin/rm -rf ${SYNC_DIR}/SITECONF/${TAR_DIR}
            fi
            continue
         fi
         /bin/touch ${SYNC_DIR}/SITECONF/.timestamp
         /bin/sed -i "/^${SITE}:/d" ${SYNC_DIR}/SITECONF/.timestamp
      fi
      #
      echo "   moving tar area into place"
      /bin/mv ${SYNC_DIR}/SITECONF/${TAR_DIR} ${SYNC_DIR}/SITECONF/${SITE} 1>>${ERR_FILE} 2>&1
      if [ $? -ne 0 ]; then
         # this is bad, so we better re-try:
         /bin/sync
         /bin/sleep 3
         echo "   re-trying move of ${SITE} area" >> ${ERR_FILE}
         /bin/mv ${SYNC_DIR}/SITECONF/${TAR_DIR} ${SYNC_DIR}/SITECONF/${SITE} 1>>${ERR_FILE} 2>&1
      fi
      RC=$?
      if [ ${RC} -ne 0 ]; then
         FAIL=1
         MSG="failed to move area of ${SITE}, mv=${RC}"
         echo "   ${MSG}"
         if [ ! -t 0 ]; then
            echo "${MSG}" >> ${ERR_FILE}
            echo "" >> ${ERR_FILE}
            /bin/rm -rf ${SYNC_DIR}/SITECONF/${TAR_DIR}
         fi
         continue
      fi
      list_sites_updated="$list_sites_updated $SITE"
   fi
   #
   echo "   updating CVMFS timestamp of site"
   /bin/touch ${SYNC_DIR}/SITECONF/.timestamp
   /bin/sed -i "/^${SITE}:/d" ${SYNC_DIR}/SITECONF/.timestamp 1>/dev/null 2>&1
   /usr/bin/awk -F: '{if($1=="'${SITE}'"){print $0}}' ${TMP_AREA}/.timestamp >> ${SYNC_DIR}/SITECONF/.timestamp
done
if [ ${FAIL} -ne 0 ]; then
   MSG="failed to update SITECONF in SYNC_DIR"
   echo ""
   /bin/cat ${ERR_FILE}
   echo "   ${MSG}"
   if [ ! -t 0 ]; then
      /usr/bin/Mail -s "$0 ${MSG}" ${EMAIL_ADDR} < ${ERR_FILE}
   fi
   exit 1
fi

#
# if there are sites that are removed from gitlab or sitedb and UPDATE_SITES is empty,
# we need to make sure those sites are deleted from /cvmfs/cms.cern.ch/SITECONF and those
# sites should be added to the UPDATED_SITES list
#
#if [ "x$UPDATED_SITES" == "x" ] ; then
#echo DEBUG updated_sites are empty
#
# Ensure the $HOME/SITECONF/SITECONF has some content
if [ $(ls $SYNC_DIR/SITECONF 2>/dev/null | wc -l) -le 1 ] ; then
      echo ERROR $SYNC_DIR/SITECONF empty
      printf "functions-cms-cvmfs-mgmt: check_and_update_siteconf () ERROR $SYNC_DIR/SITECONF empty\nls $SYNC_DIR/SITECONF\necho INFO probably execute this command: rsync -arzuvp --exclude=.cvmfscatalog --delete ${rsync_name} $rsync_source/" | mail -s "ERROR: check_and_update_siteconf() $SYNC_DIR/SITECONF empty" $notifytowhom      
      exit 1
fi
sites_cvmfs=$(ls /cvmfs/cms.cern.ch/SITECONF | sort -u | grep T[0-9])
sites_sync_dir=$(ls $SYNC_DIR/SITECONF | sort -u | grep T[0-9])
   
for s in $sites_cvmfs ; do
    for s_sync in $sites_sync_dir ; do echo $s_sync ; done | grep -q $s
    if [ $? -ne 0 ] ; then
       echo DEBUG $s REMOVED from gitlab or sitedb
       for s_u in $list_sites_updated ; do echo $s_u ; done | grep -q $s
       [ $? -eq 0 ] || list_sites_updated="$list_sites_updated $s"
    fi
done
#fi
echo UPDATED_SITES=\"$(echo $list_sites_updated)\"
#[ $(expr $(date +%H) % $EVERY_X_HOUR) -eq 0 ] && { HOUR=$(date +%H) ; printf "$(basename $0) $(date) \nHOUR=$HOUR so ignore timestamp for once \nUPDATED_SITES=$UPDATED_SITES\n" | mail -s "HOUR=$HOUR so ignore timestamp for once" $EMAIL_ADDR ; } ;

#echo UPDATED_SITES=
#cp -pR /cvmfs/cms.cern.ch/SITECONF/local ${SYNC_DIR}/SITECONF/
[ -L ${SYNC_DIR}/SITECONF/local ] || ln  -s '$(CMS_LOCAL_SITE)' ${SYNC_DIR}/SITECONF/local
/bin/rm ${ERR_FILE} 1>/dev/null 2>&1
# #############################################################################



# release space_mon lock:
# -----------------------
echo "Releasing lock for cvmfs/stcnf_updt"
/bin/rm ${EXC_LOCK}
EXC_LOCK=""
# #############################################################################



exit 0
