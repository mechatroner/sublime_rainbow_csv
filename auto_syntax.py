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


def get_syntax_name(delim, policy):
    assert policy in ['Standard', 'Simple']
    if delim == '\t' and policy == 'Simple':
        return 'TSV (Rainbow)'
    if delim == ',' and policy == 'Standard':
        return 'CSV (Rainbow)'
    return 'Rainbow CSV {} {}'.format(delim, policy)


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
    scope = 'rbcsmn' + ''.join([str(ord(d)) for d in delim])
    name = get_syntax_name(delim, 'Simple')
    result = simple_header_template.format(name, scope, scope)
    num_contexts = len(rainbow_scope_names)
    for context_id in range(num_contexts):
        result += '\n'
        result += make_simple_context(delim, context_id, num_contexts)
    return result


def make_sublime_syntax_standard(delim):
    scope = 'rbcstn' + ''.join([str(ord(d)) for d in delim])
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

