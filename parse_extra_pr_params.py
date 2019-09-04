from __future__ import print_function
import json
import re
from process_pr import format
from process_pr import CMSSW_PR_PATTERN, CMSDIST_PR_PATTERN,\
    CMSSW_QUEUE_PATTERN, ARCH_PATTERN, CMSSW_RELEASE_QUEUE_PATTERN, WF_PATTERN, TEST_REGEXP

regexp_map = { "workflows" : WF_PATTERN, "cmssw_pr" : CMSSW_PR_PATTERN, "cmsdist_pr" : CMSDIST_PR_PATTERN,
               "release_queue" : CMSSW_RELEASE_QUEUE_PATTERN , "arch" : ARCH_PATTERN , "cmssw" : CMSSW_QUEUE_PATTERN }

full_cmssw_pattern = "(true|false)"
cmssw_extra_prs_ONLY_pttrn = "(cms-sw\/cmssw#+[0-9][0-9]*)"
cmsdist_extra_prs_ONLY_pttrn = "(cms-sw\/cmsdist#+[0-9][0-9]*)"
cmsdata_extra_prs = "(cmsdata\/[a-zA-Z0-9][a-zA-Z0-9]*#+[0-9][0-9]*)"

short_map = { "workflows" : WF_PATTERN , "arch" : ARCH_PATTERN , "cmssw_queue_pattern" : CMSSW_QUEUE_PATTERN,
                      "cmsdist_prs" : cmsdist_extra_prs_ONLY_pttrn, # matches more then one
                      "cmssw_prs" : cmssw_extra_prs_ONLY_pttrn, # matches more then one
                      "cmsdata_prs" : cmsdata_extra_prs,
                      "full_cmssw" : full_cmssw_pattern, #
                      "cmssw_release_queue_pattern" : CMSSW_RELEASE_QUEUE_PATTERN
                      }

def parse_extra_params(full_comment):
    # check first line
    if not "test parameters" in full_comment.splitlines()[0]:
        print("not a proper multiline comment")
        return {}  # return empty

    matched_extra_args = dict()
    for l in full_comment.splitlines():

        for k, pttrn in short_map.items():
            #pttrn = cherry_picked_map[k]
            if l.find('=') is -1:
                # only the first line should match this, or the = is missing in the comment, skip if it's missing
                continue

            line_args = l.replace(" ", "")

            if line_args.find(',') is -1:
                extra_vals = [line_args.split("=")[1]]
            else:
                line_args = line_args.replace("=", " ")
                extra_vals = [x for x in re.compile('\s*[,|\s+]\s*').split(line_args)]
            list_of_matches = []

            for v in extra_vals:
                if re.match(pttrn, v):
                    list_of_matches.append(v)

            if list_of_matches:
                matched_extra_args[k] = list_of_matches

    return matched_extra_args

with open("multiline_github_comment_example.txt") as gh_comment_data:
    file_lines = gh_comment_data.read()

#print(TEST_REGEXP)
#print(CMSDIST_PR_PATTERN)
multiline_args = parse_extra_params(file_lines)
print(json.dumps(multiline_args, indent=1, sort_keys=True))