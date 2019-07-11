#!/usr/bin/env python
from __future__ import print_function
from es_utils import get_indexes, delete_index, send_request
import sys
import json
from time import sleep

if __name__ == "__main__":

    pattern = sys.argv[1]
    indexes = get_indexes('cmssdt-'+pattern+'*').splitlines()
    indexes_name_only = []
    for i in indexes:
        if 'open' not in i and 'green' not in i:
            continue
        list_of_recs = i.split()
        print(list_of_recs)
        for j in list_of_recs:
            if 'cmssdt-' in j:
                indexes_name_only.append(j)

    print('indexes names only')
    print(indexes_name_only)
    for i in indexes_name_only:
        print(i)
        current_idx = i
        tmp_idx = i+'_temppp'
        request_data = json.dumps({"source":{"index": current_idx }, "dest":{"index": tmp_idx} })
        print('request for reindex body: ', request_data)
        request_finished_properly = send_request('_reindex/', request_data, method='POST')
        if request_finished_properly:
            print('first reindexing complete, delete')
            delete_index(current_idx)
        else:
            print('reindexing failed for ', current_idx, ' to ',tmp_idx, ', crash the jenkins job')
            exit(-1)

        # index was just created, wait 10 seconds before trying to read it. requests were failing otherwise
        # assumption is not readable yet ()
        sleep(10)

        request_data = {"source":{"index": tmp_idx }, "dest":{"index": current_idx} }
        request_finished_properly = send_request('_reindex/', request_data, method='POST')
        if request_finished_properly:
            delete_index(tmp_idx)
        else:
            print('reindexing failed for ', tmp_idx, ' to ', current_idx, ', crash the jenkins job, try manually')
            exit(-1)

