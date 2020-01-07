from __future__ import print_function
import sys
from time import time
from ROOT import *
import json

if __name__ == "__main__":
    
    ifile = sys.argv[1]
    with open(ifile, 'r') as input_json:
        stats = json.load(input_json)

    nbins = len(stats)
    nstats = len(stats[0])
    print('bins: ', nbins, ' stats:', nstats)
    histos = {}

    stats_keys = stats[0].keys()
    
    for i in stats_keys:
        histos[i] = TH1F(i, i, nbins, 0, nbins)

    print(stats_keys, len(stats_keys))
    count  = 0
    for i in stats:
        for k in stats_keys:
            v = i[k]
            histos[k].SetBinContent(count, v)
        
        count = count+1

    for h in histos.keys():
        histos[h].SaveAs(h+".root")
