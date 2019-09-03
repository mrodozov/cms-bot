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

cherry_picked_map = { "workflows" : WF_PATTERN , "arch" : ARCH_PATTERN , "cmssw" : CMSSW_QUEUE_PATTERN,
                      "cmsdist_prs" : cmsdist_extra_prs_ONLY_pttrn, # matches more then one
                      "cmssw_prs" : cmssw_extra_prs_ONLY_pttrn, # matches more then one
                      "full_cmssw" : full_cmssw_pattern
                      }

def parse_extra_params(full_comment):
    # first line
    if not "test parameters" in full_comment.splitlines()[0]:
        print("not a proper multiline comment")
        #return "something mathing the default structure but empty, or maybe return None"
        return None

    matched_extra_args = dict()

    #if not full_comment.split('/n')[0] is "test parameters":
    for l in full_comment.splitlines():
        match = False
        extra_arg = None
        extra_vals = None
        print('\n --- \n', l)
        for k in cherry_picked_map:
            pttrn = cherry_picked_map[k]
            if l.find('=') is -1:
                # only the first line should match this, or the = is missing in the comment, skip if it's missing
                continue
            print('  keyword:', k, '\n  pattern: ', pttrn, '\n  full line: ' , l)
            line_args = re.sub(r"^\s+", "", l.split('=', 1)[1], flags=re.UNICODE) # trims white spaces in the beginning
            print(line_args, ' lenght: ', len(line_args))
            #compiled_pattern = re.compile(pttrn) #re.I is to ignore upper lower case

            m = re.match(pttrn, line_args)
            #print(m)

            if m:
                match = m
                extra_arg = k
                # create new key with
                extra_vals = line_args.split(',')

                


                #matched_extra_args[extra_arg] = extra_vals
                #print('split args: ' , line_args.split(','))
                #print(matched_extra_args)
                # only one pattern can match ? actually not :/ collect a one to one pattern match to avoid bugs

                # or don't brake but collect all matches in another list.
                # so have two lists per line - one with the patterns and one with the lines

                matched_extra_args[extra_arg] = extra_vals

        if match:
            #matched_extra_args[extra_arg] = extra_vals
            print(' -- FOUND MATCH ! ', extra_arg, extra_vals)

        #else:
        #    print('-- no match \n ---')

    print('struct is')
    print(json.dumps(matched_extra_args, indent=1, sort_keys=True))

    # if first the



with open("multiline_github_comment_example.txt") as gh_comment_data:
    file_lines = gh_comment_data.read()

#print(TEST_REGEXP)
#print(CMSDIST_PR_PATTERN)
parse_extra_params(file_lines)
