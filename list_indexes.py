#!/usr/bin/env python
from __future__ import print_function
import json, re, ssl
from os.path import exists
from os import getenv
from _py2with3compatibility import HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, install_opener, Request, \
  urlopen, build_opener
from es_utils import get_indexes

if __name__ == "__main__":

    indexes = get_indexes('relvals_stats_summary*').splitlines()

    for i in indexes:
        print(i)
