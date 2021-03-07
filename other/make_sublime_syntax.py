#!/usr/bin/env python

import sys
import os
import argparse
import random
import re

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parent_dir) 

import auto_syntax


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
    policy = auto_syntax.filename_policy_map[policy]
    if delim == '\t' and policy == 'Simple':
        return 'TSV (Rainbow)'
    if delim == ',' and policy == 'Standard':
        return 'CSV (Rainbow)'
    return 'Rainbow CSV {} {}'.format(name_normalize(delim), policy)


def write_sublime_syntax(delim, policy, dst_dir, old_names):
    # TODO get rid of this
    if old_names:
        syntax_file_name = get_syntax_file_name_old(delim, policy) + '.sublime-syntax'
    else:
        syntax_file_name = auto_syntax.get_syntax_file_basename(delim, policy)
    syntax_path = os.path.join(dst_dir, syntax_file_name)
    syntax_text = auto_syntax.make_sublime_syntax(delim, policy)
    with open(syntax_path, 'w') as dst:
        dst.write(syntax_text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--make_grammars_prod', help='make and put grammars into DIR')
    parser.add_argument('--make_grammars_old', help='make and put grammars into DIR')
    parser.add_argument('--dbg_delim', help='Run in debug mode: print single grammar with delim')
    parser.add_argument('--dbg_policy', help='Run in debug mode: print single grammar with policy')
    args = parser.parse_args()

    if args.make_grammars_old:
        dst_dir = args.make_grammars_old
        delims = auto_syntax.get_pregenerated_delims()
        standard_delims = '\t|,;'
        for delim in delims:
            if standard_delims.find(delim) != -1:
                write_sublime_syntax(delim, 'quoted', dst_dir, old_names=True)
            write_sublime_syntax(delim, 'simple', dst_dir, old_names=True)
        return

    if args.make_grammars_prod:
        dst_dir = args.make_grammars_prod
        delims = auto_syntax.get_pregenerated_delims()
        standard_delims = ',;'
        for delim in delims:
            if standard_delims.find(delim) != -1:
                write_sublime_syntax(delim, 'quoted', dst_dir, old_names=False)
                write_sublime_syntax(delim, 'quoted_rfc', dst_dir, old_names=False)
            write_sublime_syntax(delim, 'simple', dst_dir, old_names=False)
        return

    delim = args.dbg_delim
    policy = args.dbg_policy

    grammar = auto_syntax.make_sublime_syntax(delim, policy)
    print(grammar)



if __name__ == '__main__':
    main()
