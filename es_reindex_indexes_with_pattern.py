#!/usr/bin/env python
from __future__ import print_function
from es_utils import get_indexes, delete_index, send_request
import sys
import json

if __name__ == "__main__":

    pattern = sys.argv[1]
    indexes = get_indexes('cmssdt-'+pattern+'*').splitlines()
    indexes_name_only = []
    for i in indexes:
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
        tmp_idx = i+'_tmp'
        request_data = json.dumps({"source":{"index": current_idx }, "dest":{"index": tmp_idx} })
        print(str(request_data))
        send_request('_reindex', request_data, method='POST')
        #delete_index(current_idx)
        #request_data = {"source":{"index": tmp_idx }, "dest":{"index": current_idx} }
        #send_request('_reindex', request_data, method='POST')
        #delete_index(tmp_idx)


