#!/usr/bin/env python

import sys
import os
import argparse
import random
import re

# TODO this code can be moved into sublime rainbow_csv plugin to generate syntaxes in runtime

simple_header_template = '''%YAML 1.2
---
name: {}
file_extensions: [{}]
scope: text.{}


contexts:
    main:
        - match: '^'
          push: rainbow1
'''


standard_header_template = '''%YAML 1.2
---
name: {}
file_extensions: [{}]
scope: text.{}


contexts:
    main:
        - match: '^'
          push: rainbow1

    quoted_field:
        - match: '""'
          scope: meta.rainbow.double-quote-escaped
        - match: '"'
          pop: true
        - match: '$'
          pop: true
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
    assert policy in ['Standard', 'Simple']
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


def make_standard_context(delim, context_id, num_contexts, indent='    '):
    result_lines = []
    next_context_id = (context_id + 1) % num_contexts
    context_header = "{}:".format(get_context_name(context_id))
    result_lines.append("- meta_scope: {}".format(rainbow_scope_names[context_id]))
    result_lines.append("- match: '{}'".format(yaml_escape(oniguruma_regular_escape(delim))))
    result_lines.append("  set: {}".format(get_context_name(next_context_id)))
    result_lines.append("- match: '$'")
    result_lines.append("  pop: true")
    result_lines.append("- match: '\"'")
    result_lines.append("  push: quoted_field")
    result_lines = [indent + v for v in result_lines]
    result_lines = [context_header] + result_lines
    result_lines = [indent + v for v in result_lines]
    return '\n'.join(result_lines) + '\n'


def make_sublime_syntax_simple(delim):
    scope = 'rbcsmn{}'.format(ord(delim))
    name = get_syntax_name(delim, 'Simple')
    result = simple_header_template.format(name, scope, scope)
    num_contexts = len(rainbow_scope_names)
    for context_id in range(num_contexts):
        result += '\n'
        result += make_simple_context(delim, context_id, num_contexts)
    return result


def make_sublime_syntax_standard(delim):
    scope = 'rbcstn{}'.format(ord(delim))
    name = get_syntax_name(delim, 'Standard')
    result = standard_header_template.format(name, scope, scope)
    num_contexts = len(rainbow_scope_names)
    for context_id in range(num_contexts):
        result += '\n'
        result += make_standard_context(delim, context_id, num_contexts)
    return result


def make_sublime_syntax(delim, policy):
    assert policy in ['Standard', 'Simple']
    if policy == 'Standard':
        return make_sublime_syntax_standard(delim)
    else:
        return make_sublime_syntax_simple(delim)


def get_prod_delims():
    delims = [chr(i) for i in range(32, 127)]
    delims.append('\t')
    delims = [delim for delim in delims if re.match('^[a-zA-Z0-9]$', delim) is None]
    return delims
            

def write_sublime_syntax(delim, policy, dst_dir):
    name = get_syntax_name(delim, policy) + '.sublime-syntax'
    syntax_path = os.path.join(dst_dir, name)
    syntax_text = make_sublime_syntax(delim, policy)
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

    grammar = make_sublime_syntax(delim, policy)
    print grammar



if __name__ == '__main__':
    main()
