import json

def getListOfWFsFromFile(json_file, list_of_wfs, list_of_steps):

    json_obj = None
    filtered_obj = []
    with open(json_file, 'r') as jf:
        json_obj = json.load(jf)

    for i in json_obj:

        if i['_source']['workflow'] in list_of_wfs:
            filtered_obj.append(i['_source'])

    return filtered_obj

def separateFieldsOnTimestamp(object, stamp, list_of_wfs, list_of_fields):

    before = {}
    after = {}
    for wf in list_of_wfs:
        before[wf] = {}
        after[wf] = {}
        for field in list_of_fields:
            before[wf][field] = []
            after[wf][field] = []

    for i in object:
        wf = i['workflow']
        for field in list_of_fields:
            if i['step'] in list_of_steps:
                if int(i['@timestamp']) >= stamp:
                    after[wf][field].append(i[field] / 1048576)
                else: before[wf][field].append(i[field] / 1048576)

    return before, after

if __name__ == "__main__":

    list_of_wfs = ['10859.0']
    list_of_steps = ['step4']
    list_of_fields = ['rss_75', 'rss_25', 'rss_avg','rss_max']
    jfile = 'firstout.json'

    res = getListOfWFsFromFile(jfile, list_of_wfs, list_of_steps)

    print json.dumps(res, indent=2, sort_keys=True, separators=(',', ': '))
    with open('filtered.json', 'w') as filtered_result:
        filtered_result.write(json.dumps(res, indent=2, sort_keys=True, separators=(',', ': ')))

    stamp = 1524772800000

    res = None
    with open('filtered.json', 'r') as readf:
        res = json.load(readf)

    before, after = separateFieldsOnTimestamp(res, stamp, list_of_wfs, list_of_fields)

    for i in list_of_wfs:
        print i
        print before[i]['rss_max']
        print after[i]['rss_max']
        print len(before[i]['rss_max']) , len(after[i]['rss_max'])

