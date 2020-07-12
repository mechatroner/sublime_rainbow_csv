#!/usr/bin/env python

import sys
import os
import argparse
import random
import re

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parent_dir) 

import auto_syntax


def get_prod_delims():
    delims = [chr(i) for i in range(32, 127)]
    delims.append('\t')
    delims = [delim for delim in delims if re.match('^[a-zA-Z0-9]$', delim) is None]
    return delims
            

def name_normalize(delim):
    if delim == '<':
        return 'less-than'
    if delim == '>':
        return 'greater-than'
    if delim == ':':
        return 'colon'
    if delim == '"':
        return 'double-quote'
    if delim == '/':
        return 'slash'
    if delim == '\\':
        return 'backslash'
    if delim == '|':
        return 'pipe'
    if delim == '?':
        return 'question-mark'
    if delim == '*':
        return 'asterisk'
    if delim == '\t':
        return 'tab'
    if delim == ' ':
        return 'space'
    return '[{}]'.format(delim)


def get_syntax_file_name_old(delim, policy):
    assert policy in ['Standard', 'Simple']
    if delim == '\t' and policy == 'Simple':
        return 'TSV (Rainbow)'
    if delim == ',' and policy == 'Standard':
        return 'CSV (Rainbow)'
    return 'Rainbow CSV {} {}'.format(name_normalize(delim), policy)


def write_sublime_syntax(delim, policy, dst_dir):
    syntax_file_name = get_syntax_file_name_old(delim, policy) + '.sublime-syntax'
    syntax_path = os.path.join(dst_dir, syntax_file_name)
    syntax_text = auto_syntax.make_sublime_syntax(delim, policy)
    with open(syntax_path, 'w') as dst:
        dst.write(syntax_text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delim', help='Delim')
    parser.add_argument('--policy', help='Policy')
    parser.add_argument('--make_grammars_prod', help='make and put grammars into DIR')
    args = parser.parse_args()

    if args.make_grammars_prod:
        dst_dir = args.make_grammars_prod
        delims = get_prod_delims()
        standard_delims = '\t|,;'
        for delim in delims:
            if standard_delims.find(delim) != -1:
                write_sublime_syntax(delim, 'Standard', dst_dir)
            write_sublime_syntax(delim, 'Simple', dst_dir)
        return

    delim = args.delim
    policy = args.policy

    grammar = auto_syntax.make_sublime_syntax(delim, policy)
    print(grammar)



if __name__ == '__main__':
    main()
