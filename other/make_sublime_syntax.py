#!/usr/bin/env python

import sys
import os
import argparse
import random

# TODO this code can be moved into sublime rainbow_csv plugin to generate syntaxes in runtime

simple_header_template = '''%YAML 1.2
---
name: CSV ({})
file_extensions: [{}]
scope: text.{}


contexts:
    main:
        - match: "^"
          push: rainbow1
'''


rainbow_scope_names = [
    'rainbow1',
    'keyword.rainbow2',
    'entity.name.rainbow3',
    'comment.rainbow4',
    'string.rainbow5',
    'entity.name.tag.rainbow6',
    'storage.type.rainbow7',
    'support.rainbow8',
    'constant.language.rainbow9',
    'variable.language.rainbow10'
]


def oniguruma_regular_escape(delim):
    single_escape_chars = r'\/|.$^*()[]+?'
    if single_escape_chars.find(delim) != -1:
        return r'\{}'.format(delim)
    if delim == '\t':
        return r'\t'
    return delim


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


def get_syntax_name(delim, policy):
    if delim == '\t' and policy == 'Simple':
        return 'TSV (Rainbow)'
    if delim == ',' and policy == 'Standard':
        return 'CSV (Rainbow)'
    return 'Rainbow {} {}'.format(name_normalize(delim), policy)


def yaml_escape(data):
    return data.replace("'", "''")


def get_context_name(context_id):
    return "rainbow{}".format(context_id + 1)


def make_simple_context(delim, context_id, num_contexts, indent='    '):
    result_lines = []
    next_context_id = (context_id + 1) % num_contexts
    context_header = "{}:".format(get_context_name(context_id))
    result_lines.append("- meta_scope: {}".format(rainbow_scope_names[context_id]))
    result_lines.append("- match: '{}'".format(yaml_escape(oniguruma_regular_escape(delim))))
    result_lines.append("  set: {}".format(get_context_name(next_context_id)))
    result_lines.append("- match: '$'")
    result_lines.append("  pop: true")
    result_lines = [indent + v for v in result_lines]
    result_lines = [context_header] + result_lines
    result_lines = [indent + v for v in result_lines]
    return '\n'.join(result_lines) + '\n'


def make_sublime_syntax_simple(delim):
    scope = 'rbcsmn{}'.format(ord(delim))
    name = get_syntax_name(delim, 'simple')
    name += ' new' #FIXME
    result = simple_header_template.format(name, scope, scope)
    num_contexts = len(rainbow_scope_names)
    for context_id in range(num_contexts):
        result += '\n'
        result += make_simple_context(delim, context_id, num_contexts)
    return result





def make_sublime_syntax(delim, policy):
    assert policy in ['quoted', 'simple']
    if policy == 'quoted':
        return make_sublime_syntax_quoted(delim)
    else:
        return make_sublime_syntax_simple(delim)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delim', help='Delim')
    parser.add_argument('--policy', help='Policy')
    #parser.add_argument('--verbose', action='store_true', help='Run in verbose mode')
    #parser.add_argument('--num_iter', type=int, help='number of iterations option')
    #parser.add_argument('file_name', help='example of positional argument')
    args = parser.parse_args()


    delim = args.delim
    policy = args.policy

    grammar = make_sublime_syntax(delim, policy)
    print grammar

if __name__ == '__main__':
    main()
