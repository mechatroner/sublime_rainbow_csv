# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

import sys
import os
import re
import importlib
import codecs
import tempfile
import random
import shutil
import time
from collections import defaultdict


##########################################################################
#
# RBQL: RainBow Query Language
# Authors: Dmitry Ignatovich, ...
#
#
##########################################################################

# This module must be both python2 and python3 compatible

# This module works with records only. It is CSV-agnostic.
# Do not add CSV-related logic or variables/functions/objects like "delim", "separator" etc


# TODO cosmetic refactoring: get rid of functions with "_py" suffix

# TODO new feature: allow record iterator provide custom column names.

# TODO catch exceptions in user expression to report the exact place where it occured: "SELECT" expression, "WHERE" expression, etc

# TODO gracefuly handle unknown encoding: generate RbqlIOHandlingError

# TODO modify ARRAY_AGG: it should return array instead of joined string
# TODO document the second callback argument of ARRAY_AGG in the README.md


GROUP_BY = 'GROUP BY'
UPDATE = 'UPDATE'
SELECT = 'SELECT'
JOIN = 'JOIN'
INNER_JOIN = 'INNER JOIN'
LEFT_JOIN = 'LEFT JOIN'
STRICT_LEFT_JOIN = 'STRICT LEFT JOIN'
ORDER_BY = 'ORDER BY'
WHERE = 'WHERE'
LIMIT = 'LIMIT'
EXCEPT = 'EXCEPT'



class RbqlRuntimeError(Exception):
    pass

class RbqlIOHandlingError(Exception):
    pass

class RbqlParsingError(Exception):
    pass


def exception_to_error_info(e):
    exceptions_type_map = {
        'RbqlRuntimeError': 'query execution',
        'RbqlParsingError': 'query parsing',
        'RbqlIOHandlingError': 'IO handling'
    }

    error_type = 'unexpected'
    error_msg = str(e)
    for k, v in exceptions_type_map.items():
        if type(e).__name__.find(k) != -1:
            error_type = v
    return {'type': error_type, 'message': error_msg}


def rbql_meta_format(template_src, meta_params):
    for key, value in meta_params.items():
        # TODO make special replace for multiple statements, like in update, it should be indent-aware. values should be a list in this case to avoid join/split
        template_src_upd = template_src.replace(key, value)
        assert template_src_upd != template_src
        template_src = template_src_upd
    assert template_src.find('__RBQLMP__') == -1, 'Unitialized __RBQLMP__ template variables found'
    return template_src


def strip_comments(cline):
    cline = cline.strip()
    if cline.startswith('#'):
        return ''
    return cline


def parse_join_expression(src):
    match = re.match(r'(?i)^ *([^ ]+) +on +([ab][0-9]+) *== *([ab][0-9]+) *$', src)
    if match is None:
        raise RbqlParsingError('Invalid join syntax. Must be: "<JOIN> /path/to/B/table on a<i> == b<j>"')
    table_id = match.group(1)
    avar = match.group(2)
    bvar = match.group(3)
    if avar[0] == 'b':
        avar, bvar = bvar, avar
    if avar[0] != 'a' or bvar[0] != 'b':
        raise RbqlParsingError('Invalid join syntax. Must be: "<JOIN> /path/to/B/table on a<i> == b<j>"')
    lhs_join_var = 'safe_join_get(afields, {})'.format(int(avar[1:]) - 1)
    rhs_key_index = int(bvar[1:]) - 1
    return (table_id, lhs_join_var, rhs_key_index)


def generate_init_statements(column_vars, indent):
    init_statements = []
    for var_name in column_vars:
        var_group = var_name[0]
        zero_based_idx = int(var_name[1:]) - 1
        if var_group == 'a':
            init_statements.append('{} = safe_get(afields, {})'.format(var_name, zero_based_idx))
        if var_group == 'b':
            init_statements.append('{} = safe_get(bfields, {}) if bfields is not None else None'.format(var_name, zero_based_idx))
    for i in range(1, len(init_statements)):
        init_statements[i] = indent + init_statements[i]
    result = '\n'.join(init_statements)
    return result



def replace_star_count(aggregate_expression):
    return re.sub(r'(^|(?<=,)) *COUNT\( *\* *\) *($|(?=,))', ' COUNT(1)', aggregate_expression, flags=re.IGNORECASE).lstrip(' ')


def replace_star_vars(rbql_expression):
    rbql_expression = re.sub(r'(?:^|,) *\* *(?=, *\* *($|,))', '] + star_fields + [', rbql_expression)
    rbql_expression = re.sub(r'(?:^|,) *\* *(?:$|,)', '] + star_fields + [', rbql_expression)
    return rbql_expression


def translate_update_expression(update_expression, indent):
    translated = re.sub('(?:^|,) *a([1-9][0-9]*) *=(?=[^=])', '\nsafe_set(up_fields, \\1,', update_expression)
    update_statements = translated.split('\n')
    update_statements = [s.strip() for s in update_statements]
    if len(update_statements) < 2 or update_statements[0] != '':
        raise RbqlParsingError('Unable to parse "UPDATE" expression')
    update_statements = update_statements[1:]
    update_statements = ['{})'.format(s) for s in update_statements]
    for i in range(1, len(update_statements)):
        update_statements[i] = indent + update_statements[i]
    translated = '\n'.join(update_statements)
    return translated


def translate_select_expression_py(select_expression):
    translated = replace_star_count(select_expression)
    translated = replace_star_vars(translated)
    translated = translated.strip()
    if not len(translated):
        raise RbqlParsingError('"SELECT" expression is empty')
    return '[{}]'.format(translated)


def separate_string_literals_py(rbql_expression):
    # The regex is improved expression from here: https://stackoverflow.com/a/14366904/2898283
    string_literals_regex = r'''(\"\"\"|\'\'\'|\"|\')((?<!\\)(\\\\)*\\\1|.)*?\1'''
    matches = list(re.finditer(string_literals_regex, rbql_expression))
    string_literals = list()
    format_parts = list()
    idx_before = 0
    for m in matches:
        literal_id = len(string_literals)
        string_literals.append(m.group(0))
        format_parts.append(rbql_expression[idx_before:m.start()])
        format_parts.append('###RBQL_STRING_LITERAL###{}'.format(literal_id))
        idx_before = m.end()
    format_parts.append(rbql_expression[idx_before:])
    format_expression = ''.join(format_parts)
    format_expression = format_expression.replace('\t', ' ')
    return (format_expression, string_literals)


def combine_string_literals(backend_expression, string_literals):
    for i in reversed(range(len(string_literals))):
        backend_expression = backend_expression.replace('###RBQL_STRING_LITERAL###{}'.format(i), string_literals[i])
    return backend_expression


def locate_statements(rbql_expression):
    statement_groups = list()
    statement_groups.append([STRICT_LEFT_JOIN, LEFT_JOIN, INNER_JOIN, JOIN])
    statement_groups.append([SELECT])
    statement_groups.append([ORDER_BY])
    statement_groups.append([WHERE])
    statement_groups.append([UPDATE])
    statement_groups.append([GROUP_BY])
    statement_groups.append([LIMIT])
    statement_groups.append([EXCEPT])

    result = list()
    for st_group in statement_groups:
        for statement in st_group:
            rgxp = r'(?i)(?:^| ){}(?= )'.format(statement.replace(' ', ' *'))
            matches = list(re.finditer(rgxp, rbql_expression))
            if not len(matches):
                continue
            if len(matches) > 1:
                raise RbqlParsingError('More than one "{}" statements found'.format(statement))
            assert len(matches) == 1
            match = matches[0]
            result.append((match.start(), match.end(), statement))
            break # Break to avoid matching a sub-statement from the same group e.g. "INNER JOIN" -> "JOIN"
    return sorted(result)


def separate_actions(rbql_expression):
    # TODO add more checks:
    # make sure all rbql_expression was separated and SELECT or UPDATE is at the beginning
    rbql_expression = rbql_expression.strip(' ')
    ordered_statements = locate_statements(rbql_expression)
    result = dict()
    for i in range(len(ordered_statements)):
        statement_start = ordered_statements[i][0]
        span_start = ordered_statements[i][1]
        statement = ordered_statements[i][2]
        span_end = ordered_statements[i + 1][0] if i + 1 < len(ordered_statements) else len(rbql_expression)
        assert statement_start < span_start
        assert span_start <= span_end
        span = rbql_expression[span_start:span_end]

        statement_params = dict()

        if statement in [STRICT_LEFT_JOIN, LEFT_JOIN, INNER_JOIN, JOIN]:
            statement_params['join_subtype'] = statement
            statement = JOIN

        if statement == UPDATE:
            if statement_start != 0:
                raise RbqlParsingError('UPDATE keyword must be at the beginning of the query')
            span = re.sub('(?i)^ *SET ', '', span)

        if statement == ORDER_BY:
            span = re.sub('(?i) ASC *$', '', span)
            new_span = re.sub('(?i) DESC *$', '', span)
            if new_span != span:
                span = new_span
                statement_params['reverse'] = True
            else:
                statement_params['reverse'] = False

        if statement == SELECT:
            if statement_start != 0:
                raise RbqlParsingError('SELECT keyword must be at the beginning of the query')
            match = re.match('(?i)^ *TOP *([0-9]+) ', span)
            if match is not None:
                statement_params['top'] = int(match.group(1))
                span = span[match.end():]
            match = re.match('(?i)^ *DISTINCT *(COUNT)? ', span)
            if match is not None:
                statement_params['distinct'] = True
                if match.group(1) is not None:
                    statement_params['distinct_count'] = True
                span = span[match.end():]

        statement_params['text'] = span.strip()
        result[statement] = statement_params
    if SELECT not in result and UPDATE not in result:
        raise RbqlParsingError('Query must contain either SELECT or UPDATE statement')
    assert (SELECT in result) != (UPDATE in result)
    return result


def find_top(rb_actions):
    if LIMIT in rb_actions:
        try:
            return int(rb_actions[LIMIT]['text'])
        except ValueError:
            raise RbqlParsingError('LIMIT keyword must be followed by an integer')
    return rb_actions[SELECT].get('top', None)


def indent_user_init_code(user_init_code):
    source_lines = user_init_code.split('\n')
    source_lines = ['    ' + l.rstrip() for l in source_lines]
    return '\n'.join(source_lines) + '\n'


def extract_column_vars(rbql_expression):
    rgx = '(?:^|[^_a-zA-Z0-9])([ab][1-9][0-9]*)(?:$|(?=[^_a-zA-Z0-9]))'
    matches = list(re.finditer(rgx, rbql_expression))
    return list(set([m.group(1) for m in matches]))


def translate_except_expression(except_expression):
    skip_vars = except_expression.split(',')
    skip_vars = [v.strip() for v in skip_vars]
    skip_indices = list()
    for var_name in skip_vars:
        if re.match('^a[1-9][0-9]*$', var_name) is None:
            raise RbqlParsingError('Invalid EXCEPT syntax')
        skip_indices.append(int(var_name[1:]) - 1)
    skip_indices = sorted(skip_indices)
    skip_indices = [str(v) for v in skip_indices]
    return 'select_except(afields, [{}])'.format(','.join(skip_indices))


class HashJoinMap:
    # Other possible flavors: BinarySearchJoinMap, MergeJoinMap
    def __init__(self, record_iterator, key_index):
        self.max_record_len = 0
        self.hash_map = defaultdict(list)
        self.record_iterator = record_iterator
        self.key_index = key_index


    def build(self):
        nr = 0
        while True:
            fields = self.record_iterator.get_record()
            if fields is None:
                break
            nr += 1
            num_fields = len(fields)
            self.max_record_len = max(self.max_record_len, num_fields)
            if self.key_index >= num_fields:
                raise RbqlRuntimeError('No "b' + str(self.key_index + 1) + '" field at record: ' + str(nr) + ' in "B" table')
            key = fields[self.key_index]
            self.hash_map[key].append(fields)
        self.record_iterator.finish()


    def get_join_records(self, key):
        return self.hash_map[key]


    def get_warnings(self):
        return self.record_iterator.get_warnings()



def parse_to_py(query, py_template_text, join_tables_registry, user_init_code):
    rbql_lines = query.split('\n')
    rbql_lines = [strip_comments(l) for l in rbql_lines]
    rbql_lines = [l for l in rbql_lines if len(l)]
    full_rbql_expression = ' '.join(rbql_lines)
    column_vars = extract_column_vars(full_rbql_expression)
    format_expression, string_literals = separate_string_literals_py(full_rbql_expression)
    rb_actions = separate_actions(format_expression)

    py_meta_params = dict()
    py_meta_params['__RBQLMP__user_init_code'] = user_init_code

    if ORDER_BY in rb_actions and UPDATE in rb_actions:
        raise RbqlParsingError('"ORDER BY" is not allowed in "UPDATE" queries')

    if GROUP_BY in rb_actions:
        if ORDER_BY in rb_actions or UPDATE in rb_actions:
            raise RbqlParsingError('"ORDER BY" and "UPDATE" are not allowed in aggregate queries')
        aggregation_key_expression = rb_actions[GROUP_BY]['text']
        py_meta_params['__RBQLMP__aggregation_key_expression'] = '({},)'.format(combine_string_literals(aggregation_key_expression, string_literals))
    else:
        py_meta_params['__RBQLMP__aggregation_key_expression'] = 'None'

    join_map = None
    if JOIN in rb_actions:
        rhs_table_id, lhs_join_var, rhs_key_index = parse_join_expression(rb_actions[JOIN]['text'])
        py_meta_params['__RBQLMP__join_operation'] = rb_actions[JOIN]['join_subtype']
        py_meta_params['__RBQLMP__lhs_join_var'] = lhs_join_var
        if join_tables_registry is None:
            raise RbqlParsingError('JOIN operations were disabled')
        join_record_iterator = join_tables_registry.get_iterator_by_table_id(rhs_table_id)
        if join_record_iterator is None:
            raise RbqlParsingError('Unable to use join table: "{}"'.format(rhs_table_id))
        join_map = HashJoinMap(join_record_iterator, rhs_key_index)
    else:
        py_meta_params['__RBQLMP__join_operation'] = 'VOID'
        py_meta_params['__RBQLMP__lhs_join_var'] = 'None'

    if WHERE in rb_actions:
        where_expression = rb_actions[WHERE]['text']
        if re.search(r'[^!=]=[^=]', where_expression) is not None:
            raise RbqlParsingError('Assignments "=" are not allowed in "WHERE" expressions. For equality test use "=="')
        py_meta_params['__RBQLMP__where_expression'] = combine_string_literals(where_expression, string_literals)
    else:
        py_meta_params['__RBQLMP__where_expression'] = 'True'

    if UPDATE in rb_actions:
        update_expression = translate_update_expression(rb_actions[UPDATE]['text'], ' ' * 8)
        py_meta_params['__RBQLMP__writer_type'] = 'simple'
        py_meta_params['__RBQLMP__select_expression'] = 'None'
        py_meta_params['__RBQLMP__update_statements'] = combine_string_literals(update_expression, string_literals)
        py_meta_params['__RBQLMP__is_select_query'] = 'False'
        py_meta_params['__RBQLMP__top_count'] = 'None'

    py_meta_params['__RBQLMP__init_column_vars_select'] = generate_init_statements(column_vars, ' ' * 8)
    py_meta_params['__RBQLMP__init_column_vars_update'] = generate_init_statements(column_vars, ' ' * 4)

    if SELECT in rb_actions:
        top_count = find_top(rb_actions)
        py_meta_params['__RBQLMP__top_count'] = str(top_count) if top_count is not None else 'None'
        if 'distinct_count' in rb_actions[SELECT]:
            py_meta_params['__RBQLMP__writer_type'] = 'uniq_count'
        elif 'distinct' in rb_actions[SELECT]:
            py_meta_params['__RBQLMP__writer_type'] = 'uniq'
        else:
            py_meta_params['__RBQLMP__writer_type'] = 'simple'
        if EXCEPT in rb_actions:
            py_meta_params['__RBQLMP__select_expression'] = translate_except_expression(rb_actions[EXCEPT]['text'])
        else:
            select_expression = translate_select_expression_py(rb_actions[SELECT]['text'])
            py_meta_params['__RBQLMP__select_expression'] = combine_string_literals(select_expression, string_literals)
        py_meta_params['__RBQLMP__update_statements'] = 'pass'
        py_meta_params['__RBQLMP__is_select_query'] = 'True'

    if ORDER_BY in rb_actions:
        order_expression = rb_actions[ORDER_BY]['text']
        py_meta_params['__RBQLMP__sort_key_expression'] = combine_string_literals(order_expression, string_literals)
        py_meta_params['__RBQLMP__reverse_flag'] = 'True' if rb_actions[ORDER_BY]['reverse'] else 'False'
        py_meta_params['__RBQLMP__sort_flag'] = 'True'
    else:
        py_meta_params['__RBQLMP__sort_key_expression'] = 'None'
        py_meta_params['__RBQLMP__reverse_flag'] = 'False'
        py_meta_params['__RBQLMP__sort_flag'] = 'False'

    python_code = rbql_meta_format(py_template_text, py_meta_params)
    return (python_code, join_map)


def write_python_module(python_code, dst_path):
    with codecs.open(dst_path, 'w', encoding='utf-8') as dst:
        dst.write(python_code)



class RbqlPyEnv:
    def __init__(self):
        self.env_dir_name = None
        self.env_dir = None
        self.module_path = None
        self.module_name = None

    def __enter__(self):
        tmp_dir = tempfile.gettempdir()
        self.env_dir_name = 'rbql_{}_{}'.format(time.time(), random.randint(1, 100000000)).replace('.', '_')
        self.env_dir = os.path.join(tmp_dir, self.env_dir_name)
        self.module_name = 'worker_{}'.format(self.env_dir_name)
        module_filename = '{}.py'.format(self.module_name)
        self.module_path = os.path.join(self.env_dir, module_filename)
        os.mkdir(self.env_dir)
        return self

    def import_worker(self):
        # We need to add env_dir to sys.path after worker module has been generated to avoid calling `importlib.invalidate_caches()`
        # Description of the problem: http://ballingt.com/import-invalidate-caches/
        assert os.path.exists(self.module_path), 'Unable to find generated module at {}'.format(self.module_path)
        sys.path.append(self.env_dir)
        return importlib.import_module(self.module_name)

    def remove_env_dir(self):
        # Should be called on success only: do not put in __exit__. In case of error we may need to have the generated module
        try:
            shutil.rmtree(self.env_dir)
        except Exception:
            pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            sys.path.remove(self.env_dir)
        except ValueError:
            pass


def generic_run(user_query, input_iterator, output_writer, join_tables_registry=None, user_init_code=''):
    # Join registry can cotain info about any number of tables (e.g. about one table "B" only)
    try:
        user_init_code = indent_user_init_code(user_init_code)
        rbql_home_dir = os.path.dirname(os.path.abspath(__file__))
        with codecs.open(os.path.join(rbql_home_dir, 'template.py'), encoding='utf-8') as py_src:
            py_template_text = py_src.read()
        python_code, join_map = parse_to_py(user_query, py_template_text, join_tables_registry, user_init_code)
        with RbqlPyEnv() as worker_env:
            write_python_module(python_code, worker_env.module_path)
            # TODO find a way to report module_path if exception is thrown.
            # One way is just to always create a symlink like "rbql_module_debug" inside tmp_dir.
            # It would point to the last module if lauch failed, or just a dangling ref.
            # Generated modules are not re-runnable by themselves now anyway.
            rbconvert = worker_env.import_worker()
            success = rbconvert.rb_transform(input_iterator, join_map, output_writer)
            assert success, 'Unexpected error during RBQL query execution'
            input_warnings = input_iterator.get_warnings()
            join_warnings = join_map.get_warnings() if join_map is not None else []
            output_warnings = output_writer.get_warnings()
            warnings = input_warnings + join_warnings + output_warnings
            worker_env.remove_env_dir()
            return (None, warnings)
    except Exception as e:
        error_info = exception_to_error_info(e)
        return (error_info, [])
    finally:
        input_iterator.finish()
        output_writer.finish()


def make_inconsistent_num_fields_warning(table_name, inconsistent_records_info):
    assert len(inconsistent_records_info) > 1
    inconsistent_records_info = inconsistent_records_info.items()
    inconsistent_records_info = sorted(inconsistent_records_info, key=lambda v: v[1])
    num_fields_1, record_num_1 = inconsistent_records_info[0]
    num_fields_2, record_num_2 = inconsistent_records_info[1]
    warn_msg = 'Number of fields in "{}" table is not consistent: '.format(table_name)
    warn_msg += 'e.g. record {} -> {} fields, record {} -> {} fields'.format(record_num_1, num_fields_1, record_num_2, num_fields_2)
    return warn_msg


class TableIterator:
    def __init__(self, table):
        self.table = table
        self.NR = 0
        self.fields_info = dict()

    def finish(self):
        pass

    def get_record(self):
        if self.NR >= len(self.table):
            return None
        record = self.table[self.NR]
        self.NR += 1
        num_fields = len(record)
        if num_fields not in self.fields_info:
            self.fields_info[num_fields] = self.NR
        return record

    def get_warnings(self):
        if len(self.fields_info) > 1:
            return [make_inconsistent_num_fields_warning('input', self.fields_info)]
        return []


class TableWriter:
    def __init__(self, external_table):
        self.table = external_table

    def write(self, fields):
        self.table.append(fields)

    def finish(self):
        pass

    def get_warnings(self):
        return []


class SingleTableRegistry:
    def __init__(self, table, table_name='B'):
        self.table = table
        self.table_name = table_name

    def get_iterator_by_table_id(self, table_id):
        if table_id != self.table_name:
            raise RbqlIOHandlingError('Unable to find join table: "{}"'.format(table_id))
        return TableIterator(self.table)


def table_run(user_query, input_table, output_table, join_table=None, user_init_code=''):
    input_iterator = TableIterator(input_table)
    output_writer = TableWriter(output_table)
    join_tables_registry = None if join_table is None else SingleTableRegistry(join_table)
    return generic_run(user_query, input_iterator, output_writer, join_tables_registry, user_init_code=user_init_code)
