# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

import sys
import re
import random
import time
from collections import OrderedDict, defaultdict, namedtuple

from ._version import __version__

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


# UT JSON - means json Unit Test exists for this case
# UT JSON CSV - means json csv Unit Test exists for this case


# TODO catch exceptions in user expression to report the exact place where it occured: "SELECT" expression, "WHERE" expression, etc

# TODO consider supporting explicit column names variables like "host" or "name" or "surname" - just parse all variable-looking sequences from the query and match them against available column names from the header, but skip all symbol defined in rbql_engine.py/rbql.js, user init code and python/js builtin keywords (show warning on intersection)

# TODO optimize performance: optional compilation depending on python2/python3

# TODO gracefuly handle unknown encoding: generate RbqlIOHandlingError

# TODO show warning when csv fields contain trailing spaces, at least in join mode

# TODO support custom (virtual) headers for CSV version

# TODO support RBQL variable "NL" - line number. when header is skipped it would be "2" for the first record. Also it is not equal to NR for multiline records

# TODO support option to skip comment lines (lines starting with the specified prefix)

# TODO add "inconsistent number of fields in output table" warning. Useful for queries like this: `*a1.split("|")` or `...a1.split("|")`, where num of fields in a1 is variable


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

ambiguous_error_msg = 'Ambiguous variable name: "{}" is present both in input and in join tables'
invalid_keyword_in_aggregate_query_error_msg = '"ORDER BY", "UPDATE" and "DISTINCT" keywords are not allowed in aggregate queries'

debug_mode = False

class RbqlRuntimeError(Exception):
    pass

class RbqlParsingError(Exception):
    pass

class RbqlIOHandlingError(Exception):
    pass


VariableInfo = namedtuple('VariableInfo', ['initialize', 'index'])



query_context = None


class RBQLContext:
    def __init__(self, input_iterator, output_writer, user_init_code):
        self.input_iterator = input_iterator
        self.writer = output_writer
        self.user_init_code = user_init_code

        self.unnest_list = None
        self.top_count = None

        self.like_regex_cache = dict()

        self.sort_key_expression = None
        self.reverse_sort = False

        self.aggregation_stage = 0
        self.aggregation_key_expression = None
        self.functional_aggregators = []

        self.join_map_impl = None
        self.join_map = None
        self.join_operation = None
        self.lhs_join_var_expression = None

        self.where_expression = None

        self.select_expression = None

        self.update_expressions = None

        self.variables_init_code = None



######################################


import datetime # For date operations
import os # For system operations
import math # For math operations


RBQL_VERSION = __version__


wrong_aggregation_usage_error = 'Usage of RBQL aggregation functions inside Python expressions is not allowed, see the docs'
numeric_conversion_error = 'Unable to convert value "{}" to int or float. MIN, MAX, SUM, AVG, MEDIAN and VARIANCE aggregate functions convert their string arguments to numeric values'


PY3 = sys.version_info[0] == 3


def iteritems6(x):
    if PY3:
        return x.items()
    return x.iteritems()


class InternalBadFieldError(Exception):
    def __init__(self, bad_idx):
        self.bad_idx = bad_idx


class InternalBadKeyError(Exception):
    def __init__(self, bad_key):
        self.bad_key = bad_key


class RBQLRecord:
    def __init__(self):
        self.storage = dict()

    def __getitem__(self, key):
        try:
            return self.storage[key]
        except KeyError:
            raise InternalBadKeyError(key)

    def __setitem__(self, key, value):
        self.storage[key] = value


def safe_get(record, idx):
    return record[idx] if idx < len(record) else None


def safe_join_get(record, idx):
    try:
        return record[idx]
    except IndexError:
        raise InternalBadFieldError(idx)


def safe_set(record, idx, value):
    try:
        record[idx] = value
    except IndexError:
        raise InternalBadFieldError(idx)


def like_to_regex(pattern):
    p = 0
    i = 0
    converted = ''
    while i < len(pattern):
        if pattern[i] in ['_', '%']:
            converted += re.escape(pattern[p:i])
            p = i + 1
            if pattern[i] == '_':
                converted += '.'
            else:
                converted += '.*'
        i += 1
    converted += re.escape(pattern[p:i])
    return '^' + converted + '$'


def like(text, pattern):
    matcher = query_context.like_regex_cache.get(pattern, None)
    if matcher is None:
        matcher = re.compile(like_to_regex(pattern))
        query_context.like_regex_cache[pattern] = matcher
    return matcher.match(text) is not None
LIKE = like


class RBQLAggregationToken(object):
    def __init__(self, marker_id, value):
        self.marker_id = marker_id
        self.value = value

    def __str__(self):
        raise TypeError('RBQLAggregationToken')


class UNNEST:
    def __init__(self, vals):
        if query_context.unnest_list is not None:
            # Technically we can support multiple UNNEST's but the implementation/algorithm is more complex and just doesn't worth it
            raise RbqlParsingError('Only one UNNEST is allowed per query') # UT JSON
        query_context.unnest_list = vals

    def __str__(self):
        raise TypeError('UNNEST')

unnest = UNNEST
Unnest = UNNEST


class NumHandler:
    def __init__(self, start_with_int):
        self.is_int = start_with_int
        self.string_detection_done = False
        self.is_str = False

    def parse(self, val):
        if not self.string_detection_done:
            self.string_detection_done = True
            if PY3 and isinstance(val, str):
                self.is_str = True
            if not PY3 and isinstance(val, basestring):
                self.is_str = True
        if not self.is_str:
            return val
        if self.is_int:
            try:
                return int(val)
            except ValueError:
                self.is_int = False
        try:
            return float(val)
        except ValueError:
            raise RbqlRuntimeError(numeric_conversion_error.format(val)) # UT JSON


class MinAggregator:
    def __init__(self):
        self.stats = dict()
        self.num_handler = NumHandler(True)

    def increment(self, key, val):
        val = self.num_handler.parse(val)
        cur_aggr = self.stats.get(key)
        if cur_aggr is None:
            self.stats[key] = val
        else:
            self.stats[key] = builtin_min(cur_aggr, val)

    def get_final(self, key):
        return self.stats[key]


class MaxAggregator:
    def __init__(self):
        self.stats = dict()
        self.num_handler = NumHandler(True)

    def increment(self, key, val):
        val = self.num_handler.parse(val)
        cur_aggr = self.stats.get(key)
        if cur_aggr is None:
            self.stats[key] = val
        else:
            self.stats[key] = builtin_max(cur_aggr, val)

    def get_final(self, key):
        return self.stats[key]


class SumAggregator:
    def __init__(self):
        self.stats = defaultdict(int)
        self.num_handler = NumHandler(True)

    def increment(self, key, val):
        val = self.num_handler.parse(val)
        self.stats[key] += val

    def get_final(self, key):
        return self.stats[key]


class AvgAggregator:
    def __init__(self):
        self.stats = dict()
        self.num_handler = NumHandler(False)

    def increment(self, key, val):
        val = self.num_handler.parse(val)
        cur_aggr = self.stats.get(key)
        if cur_aggr is None:
            self.stats[key] = (val, 1)
        else:
            cur_sum, cur_cnt = cur_aggr
            self.stats[key] = (cur_sum + val, cur_cnt + 1)

    def get_final(self, key):
        final_sum, final_cnt = self.stats[key]
        return float(final_sum) / final_cnt


class VarianceAggregator:
    def __init__(self):
        self.stats = dict()
        self.num_handler = NumHandler(False)

    def increment(self, key, val):
        val = self.num_handler.parse(val)
        cur_aggr = self.stats.get(key)
        if cur_aggr is None:
            self.stats[key] = (val, val ** 2, 1)
        else:
            cur_sum, cur_sum_of_squares, cur_cnt = cur_aggr
            self.stats[key] = (cur_sum + val, cur_sum_of_squares + val ** 2, cur_cnt + 1)

    def get_final(self, key):
        final_sum, final_sum_of_squares, final_cnt = self.stats[key]
        return float(final_sum_of_squares) / final_cnt - (float(final_sum) / final_cnt) ** 2


class MedianAggregator:
    def __init__(self):
        self.stats = defaultdict(list)
        self.num_handler = NumHandler(True)

    def increment(self, key, val):
        val = self.num_handler.parse(val)
        self.stats[key].append(val)

    def get_final(self, key):
        sorted_vals = sorted(self.stats[key])
        assert len(sorted_vals)
        m = int(len(sorted_vals) / 2)
        if len(sorted_vals) % 2:
            return sorted_vals[m]
        else:
            a = sorted_vals[m - 1]
            b = sorted_vals[m]
            return a if a == b else (a + b) / 2.0


class CountAggregator:
    def __init__(self):
        self.stats = defaultdict(int)

    def increment(self, key, _val):
        self.stats[key] += 1

    def get_final(self, key):
        return self.stats[key]


class ArrayAggAggregator:
    def __init__(self, post_proc=None):
        self.stats = defaultdict(list)
        self.post_proc = post_proc

    def increment(self, key, val):
        self.stats[key].append(val)

    def get_final(self, key):
        res = self.stats[key]
        if self.post_proc is not None:
            return self.post_proc(res)
        return res


class ConstGroupVerifier:
    def __init__(self, output_index):
        self.const_values = dict()
        self.output_index = output_index

    def increment(self, key, value):
        old_value = self.const_values.get(key)
        if old_value is None:
            self.const_values[key] = value
        elif old_value != value:
            raise RbqlRuntimeError('Invalid aggregate expression: non-constant values in output column {}. E.g. "{}" and "{}"'.format(self.output_index + 1, old_value, value)) # UT JSON

    def get_final(self, key):
        return self.const_values[key]


def init_aggregator(generator_name, val, post_proc=None):
    query_context.aggregation_stage = 1
    res = RBQLAggregationToken(len(query_context.functional_aggregators), val)
    if post_proc is not None:
        query_context.functional_aggregators.append(generator_name(post_proc))
    else:
        query_context.functional_aggregators.append(generator_name())
    return res


def MIN(val):
    return init_aggregator(MinAggregator, val) if query_context.aggregation_stage < 2 else val

# min = MIN - see the mad max copypaste below
Min = MIN


def MAX(val):
    return init_aggregator(MaxAggregator, val) if query_context.aggregation_stage < 2 else val

# max = MAX - see the mad max copypaste below
Max = MAX


def COUNT(_val):
    return init_aggregator(CountAggregator, 1) if query_context.aggregation_stage < 2 else 1

count = COUNT
Count = COUNT


def SUM(val):
    return init_aggregator(SumAggregator, val) if query_context.aggregation_stage < 2 else val

# sum = SUM - see the mad max copypaste below
Sum = SUM


def AVG(val):
    return init_aggregator(AvgAggregator, val) if query_context.aggregation_stage < 2 else val

avg = AVG
Avg = AVG


def VARIANCE(val):
    return init_aggregator(VarianceAggregator, val) if query_context.aggregation_stage < 2 else val

variance = VARIANCE
Variance = VARIANCE


def MEDIAN(val):
    return init_aggregator(MedianAggregator, val) if query_context.aggregation_stage < 2 else val

median = MEDIAN
Median = MEDIAN


def ARRAY_AGG(val, post_proc=None):
    # TODO consider passing array to output writer
    return init_aggregator(ArrayAggAggregator, val, post_proc) if query_context.aggregation_stage < 2 else val

array_agg = ARRAY_AGG




# Redefining builtin max, min and sum. See test_max_max.py unit test for explanation
builtin_max = max
builtin_min = min
builtin_sum = sum


def max(*args, **kwargs):
    single_arg = len(args) == 1 and not kwargs
    if single_arg:
        if PY3 and isinstance(args[0], str):
            return MAX(args[0])
        if not PY3 and isinstance(args[0], basestring):
            return MAX(args[0])
        if isinstance(args[0], int) or isinstance(args[0], float):
            return MAX(args[0])
    try:
        return builtin_max(*args, **kwargs)
    except TypeError:
        if single_arg:
            return MAX(args[0])
        raise


def min(*args, **kwargs):
    single_arg = len(args) == 1 and not kwargs
    if single_arg:
        if PY3 and isinstance(args[0], str):
            return MIN(args[0])
        if not PY3 and isinstance(args[0], basestring):
            return MIN(args[0])
        if isinstance(args[0], int) or isinstance(args[0], float):
            return MIN(args[0])
    try:
        return builtin_min(*args, **kwargs)
    except TypeError:
        if single_arg:
            return MIN(args[0])
        raise


def sum(*args):
    try:
        return builtin_sum(*args)
    except TypeError:
        if len(args) == 1:
            return SUM(args[0])
        raise




def add_to_set(dst_set, value):
    len_before = len(dst_set)
    dst_set.add(value)
    return len_before != len(dst_set)


class TopWriter(object):
    def __init__(self, subwriter):
        self.subwriter = subwriter
        self.NW = 0

    def write(self, record):
        if query_context.top_count is not None and self.NW >= query_context.top_count:
            return False
        success = self.subwriter.write(record)
        if success:
            self.NW += 1
        return success

    def finish(self):
        self.subwriter.finish()


class UniqWriter(object):
    def __init__(self, subwriter):
        self.subwriter = subwriter
        self.seen = set()

    def write(self, record):
        immutable_record = tuple(record)
        if not add_to_set(self.seen, immutable_record):
            return True
        if not self.subwriter.write(record):
            return False
        return True

    def finish(self):
        self.subwriter.finish()


class UniqCountWriter(object):
    def __init__(self, subwriter):
        self.subwriter = subwriter
        self.records = OrderedDict()

    def write(self, record):
        record = tuple(record)
        if record in self.records:
            self.records[record] += 1
        else:
            self.records[record] = 1
        return True

    def finish(self):
        for record, cnt in iteritems6(self.records):
            mutable_record = list(record)
            mutable_record.insert(0, cnt)
            if not self.subwriter.write(mutable_record):
                break
        self.subwriter.finish()


class SortedWriter(object):
    def __init__(self, subwriter):
        self.subwriter = subwriter
        self.unsorted_entries = list()

    def write(self, sort_key_value, record):
        self.unsorted_entries.append((sort_key_value, record))
        return True

    def finish(self):
        sorted_entries = sorted(self.unsorted_entries, key=lambda x: x[0])
        if query_context.reverse_sort:
            sorted_entries.reverse()
        for e in sorted_entries:
            if not self.subwriter.write(e[1]):
                break
        self.subwriter.finish()


class AggregateWriter(object):
    def __init__(self, subwriter):
        self.subwriter = subwriter
        self.aggregators = []
        self.aggregation_keys = set()

    def finish(self):
        all_keys = sorted(list(self.aggregation_keys))
        for key in all_keys:
            out_fields = [ag.get_final(key) for ag in self.aggregators]
            if not self.subwriter.write(out_fields):
                break
        self.subwriter.finish()


class InnerJoiner(object):
    def __init__(self, join_map):
        self.join_map = join_map

    def get_rhs(self, lhs_key):
        return self.join_map.get_join_records(lhs_key)


class LeftJoiner(object):
    def __init__(self, join_map):
        self.join_map = join_map
        self.null_record = [(None, join_map.max_record_len, [None] * join_map.max_record_len)]

    def get_rhs(self, lhs_key):
        result = self.join_map.get_join_records(lhs_key)
        if len(result) == 0:
            return self.null_record
        return result


class StrictLeftJoiner(object):
    def __init__(self, join_map):
        self.join_map = join_map

    def get_rhs(self, lhs_key):
        result = self.join_map.get_join_records(lhs_key)
        if len(result) != 1:
            raise RbqlRuntimeError('In "{}" each key in A must have exactly one match in B. Bad A key: "{}"'.format(STRICT_LEFT_JOIN, lhs_key)) # UT JSON
        return result


def select_except(src, except_fields):
    result = list()
    for i, v in enumerate(src):
        if i not in except_fields:
            result.append(v)
    return result


def select_simple(sort_key, out_fields):
    if query_context.sort_key_expression is not None:
        if not query_context.writer.write(sort_key, out_fields):
            return False
    else:
        if not query_context.writer.write(out_fields):
            return False
    return True


def select_aggregated(key, transparent_values):
    if query_context.aggregation_stage == 1:
        if type(query_context.writer) is SortedWriter or type(query_context.writer) is UniqWriter or type(query_context.writer) is UniqCountWriter:
            raise RbqlParsingError(invalid_keyword_in_aggregate_query_error_msg) # UT JSON
        query_context.writer = AggregateWriter(query_context.writer)
        num_aggregators_found = 0
        for i, trans_value in enumerate(transparent_values):
            if isinstance(trans_value, RBQLAggregationToken):
                num_aggregators_found += 1
                query_context.writer.aggregators.append(query_context.functional_aggregators[trans_value.marker_id])
                query_context.writer.aggregators[-1].increment(key, trans_value.value)
            else:
                query_context.writer.aggregators.append(ConstGroupVerifier(len(query_context.writer.aggregators)))
                query_context.writer.aggregators[-1].increment(key, trans_value)
        if num_aggregators_found != len(query_context.functional_aggregators):
            raise RbqlParsingError(wrong_aggregation_usage_error) # UT JSON
        query_context.aggregation_stage = 2
    else:
        for i, trans_value in enumerate(transparent_values):
            query_context.writer.aggregators[i].increment(key, trans_value)
    query_context.writer.aggregation_keys.add(key)


def select_unnested(sort_key, folded_fields):
    unnest_pos = None
    for i, trans_value in enumerate(folded_fields):
        if isinstance(trans_value, UNNEST):
            unnest_pos = i
            break
    assert unnest_pos is not None
    for v in query_context.unnest_list:
        out_fields = folded_fields[:]
        out_fields[unnest_pos] = v
        if not select_simple(sort_key, out_fields):
            return False
    return True


PROCESS_SELECT_COMMON = '''
__RBQLMP__variables_init_code
if __RBQLMP__where_expression:
    out_fields = __RBQLMP__select_expression
    if query_context.aggregation_stage > 0:
        key = __RBQLMP__aggregation_key_expression
        select_aggregated(key, out_fields)
    else:
        sort_key = __RBQLMP__sort_key_expression
        if query_context.unnest_list is not None:
            if not select_unnested(sort_key, out_fields):
                stop_flag = True
        else:
            if not select_simple(sort_key, out_fields):
                stop_flag = True
'''


PROCESS_SELECT_SIMPLE = '''
star_fields = record_a
__CODE__
'''


PROCESS_SELECT_JOIN = '''
join_matches = query_context.join_map.get_rhs(__RBQLMP__lhs_join_var_expression)
for join_match in join_matches:
    bNR, bNF, record_b = join_match
    star_fields = record_a + record_b
    __CODE__
    if stop_flag:
        break
'''


PROCESS_UPDATE_JOIN = '''
join_matches = query_context.join_map.get_rhs(__RBQLMP__lhs_join_var_expression)
if len(join_matches) > 1:
    raise RbqlRuntimeError('More than one record in UPDATE query matched a key from the input table in the join table') # UT JSON # TODO output the failed key
if len(join_matches) == 1:
    bNR, bNF, record_b = join_matches[0]
else:
    bNR, bNF, record_b = None, None, None
up_fields = record_a[:]
__RBQLMP__variables_init_code
if len(join_matches) == 1 and (__RBQLMP__where_expression):
    NU += 1
    __RBQLMP__update_expressions
if not query_context.writer.write(up_fields):
    stop_flag = True
'''


PROCESS_UPDATE_SIMPLE = '''
up_fields = record_a[:]
__RBQLMP__variables_init_code
if __RBQLMP__where_expression:
    NU += 1
    __RBQLMP__update_expressions
if not query_context.writer.write(up_fields):
    stop_flag = True
'''

# We need dummy_wrapper_for_exec function in MAIN_LOOP_BODY because otherwise "import" statements won't work as expected, see: https://github.com/mechatroner/sublime_rainbow_csv/issues/22
MAIN_LOOP_BODY = '''
def dummy_wrapper_for_exec():
    try:
        pass
        __USER_INIT_CODE__
    except Exception as e:
        raise RuntimeError('Exception while executing user-provided init code: {}'.format(e))

    NR = 0
    NU = 0
    stop_flag = False

    while not stop_flag:
        record_a = query_context.input_iterator.get_record()
        if record_a is None:
            break
        NR += 1
        NF = len(record_a)
        query_context.unnest_list = None # TODO optimize, don't need to set this every iteration
        try:
            __CODE__
        except InternalBadKeyError as e:
            raise RbqlRuntimeError('No "{}" field at record {}'.format(e.bad_key, NR)) # UT JSON
        except InternalBadFieldError as e:
            raise RbqlRuntimeError('No "a{}" field at record {}'.format(e.bad_idx + 1, NR)) # UT JSON
        except RbqlParsingError:
            raise
        except Exception as e:
            if debug_mode:
                raise
            if str(e).find('RBQLAggregationToken') != -1:
                raise RbqlParsingError(wrong_aggregation_usage_error) # UT JSON
            raise RbqlRuntimeError('At record ' + str(NR) + ', Details: ' + str(e)) # UT JSON
dummy_wrapper_for_exec()
'''


def embed_expression(parent_code, child_placeholder, child_expression):
    assert parent_code.count(child_placeholder) == 1
    assert child_expression.find('\n') == -1
    return parent_code.strip().replace(child_placeholder, child_expression) + '\n'


def embed_code(parent_code, child_placeholder, child_code):
    assert parent_code.count(child_placeholder) == 1
    parent_lines = parent_code.strip().split('\n')
    child_lines = child_code.strip().split('\n')
    placeholder_indentation = None
    for i in range(len(parent_lines)):
        pos = parent_lines[i].find(child_placeholder)
        if pos == -1:
            continue
        assert pos % 4 == 0
        placeholder_indentation = parent_lines[i][:pos]
        assert placeholder_indentation == ' ' * pos
        child_lines = [placeholder_indentation + cl for cl in child_lines]
        result = parent_lines[:i] + child_lines + parent_lines[i + 1:]
        return '\n'.join(result) + '\n'
    assert False


def generate_main_loop_code():
    is_select_query = query_context.select_expression is not None
    is_join_query = query_context.join_map is not None
    python_code = None
    where_expression = 'True' if query_context.where_expression is None else query_context.where_expression
    aggregation_key_expression = 'None' if query_context.aggregation_key_expression is None else query_context.aggregation_key_expression
    sort_key_expression = 'None' if query_context.sort_key_expression is None else query_context.sort_key_expression
    python_code = embed_code(MAIN_LOOP_BODY, '__USER_INIT_CODE__', query_context.user_init_code)
    if is_select_query:
        if is_join_query:
            python_code = embed_code(embed_code(python_code, '__CODE__', PROCESS_SELECT_JOIN), '__CODE__', PROCESS_SELECT_COMMON)
            python_code = embed_expression(python_code, '__RBQLMP__lhs_join_var_expression', query_context.lhs_join_var_expression)
        else:
            python_code = embed_code(embed_code(python_code, '__CODE__', PROCESS_SELECT_SIMPLE), '__CODE__', PROCESS_SELECT_COMMON)
        python_code = embed_code(python_code, '__RBQLMP__variables_init_code', query_context.variables_init_code)
        python_code = embed_expression(python_code, '__RBQLMP__select_expression', query_context.select_expression)
        python_code = embed_expression(python_code, '__RBQLMP__where_expression', where_expression)
        python_code = embed_expression(python_code, '__RBQLMP__aggregation_key_expression', aggregation_key_expression)
        python_code = embed_expression(python_code, '__RBQLMP__sort_key_expression', sort_key_expression)
    else:
        if is_join_query:
            python_code = embed_code(python_code, '__CODE__', PROCESS_UPDATE_JOIN)
            python_code = embed_expression(python_code, '__RBQLMP__lhs_join_var_expression', query_context.lhs_join_var_expression)
        else:
            python_code = embed_code(python_code, '__CODE__', PROCESS_UPDATE_SIMPLE)
        python_code = embed_code(python_code, '__RBQLMP__variables_init_code', query_context.variables_init_code)
        python_code = embed_code(python_code, '__RBQLMP__update_expressions', query_context.update_expressions)
        python_code = embed_expression(python_code, '__RBQLMP__where_expression', where_expression)
    return python_code



def compile_and_run():
    # TODO consider putting mad_max stuff here instead of keeping it in the global scope
    main_loop_body = generate_main_loop_code()
    compiled_main_loop = compile(main_loop_body, '<main loop>', 'exec')
    exec(compiled_main_loop)



############################################################



def exception_to_error_info(e):
    exceptions_type_map = {
        'RbqlRuntimeError': 'query execution',
        'RbqlParsingError': 'query parsing',
        'RbqlIOHandlingError': 'IO handling'
    }
    if isinstance(e, SyntaxError):
        import traceback
        etype, evalue, _etb = sys.exc_info()
        error_strings = traceback.format_exception_only(etype, evalue)
        if len(error_strings) and re.search('File.*line', error_strings[0]) is not None:
            error_strings[0] = '\n'
        error_msg = ''.join(error_strings).rstrip()
        if re.search(' like[ (]', error_msg, flags=re.IGNORECASE) is not None:
            error_msg += "\nRBQL doesn't support LIKE operator, use like() function instead e.g. ... WHERE like(a1, 'foo%bar') ... " # UT JSON
        if error_msg.lower().find(' from ') != -1:
            error_msg += "\nRBQL doesn't use \"FROM\" keyword, e.g. you can query 'SELECT *' without FROM" # UT JSON
        return ('syntax error', error_msg)
    error_type = 'unexpected'
    error_msg = str(e)
    for k, v in exceptions_type_map.items():
        if type(e).__name__.find(k) != -1:
            error_type = v
    return (error_type, error_msg)


def strip_comments(cline):
    cline = cline.strip()
    if cline.startswith('#'):
        return ''
    return cline


def combine_string_literals(backend_expression, string_literals):
    for i in range(len(string_literals)):
        backend_expression = backend_expression.replace('###RBQL_STRING_LITERAL{}###'.format(i), string_literals[i])
    return backend_expression


def parse_join_expression(src):
    src = src.strip()
    invalid_join_syntax_error = 'Invalid join syntax. Valid syntax: <JOIN> /path/to/B/table on a... == b... [and a... == b... [and ... ]]'
    match = re.search(r'^([^ ]+) +on +', src, re.IGNORECASE)
    if match is None:
        raise RbqlParsingError(invalid_join_syntax_error)
    table_id = match.group(1)
    src = src[match.end():]
    variable_pairs = []
    while True:
        match = re.search('^([^ =]+) *==? *([^ =]+)', src)
        if match is None:
            raise RbqlParsingError(invalid_join_syntax_error)
        variable_pair = (match.group(1), match.group(2))
        variable_pairs.append(variable_pair)
        src = src[match.end():]
        if not len(src):
            break
        match = re.search('^ +and +', src, re.IGNORECASE)
        if match is None:
            raise RbqlParsingError(invalid_join_syntax_error)
        src = src[match.end():]
    return (table_id, variable_pairs)


def resolve_join_variables(input_variables_map, join_variables_map, variable_pairs, string_literals):
    lhs_variables = []
    rhs_indices = []
    valid_join_syntax_msg = 'Valid JOIN syntax: <JOIN> /path/to/B/table on a... == b... [and a... == b... [and ... ]]'
    for join_var_1, join_var_2 in variable_pairs:
        join_var_1 = combine_string_literals(join_var_1, string_literals)
        join_var_2 = combine_string_literals(join_var_2, string_literals)
        if join_var_1 in input_variables_map and join_var_1 in join_variables_map:
            raise RbqlParsingError(ambiguous_error_msg.format(join_var_1))
        if join_var_2 in input_variables_map and join_var_2 in join_variables_map:
            raise RbqlParsingError(ambiguous_error_msg.format(join_var_2))
        if join_var_2 in input_variables_map:
            join_var_1, join_var_2 = join_var_2, join_var_1
        if join_var_1 in ['NR', 'a.NR', 'aNR']:
            lhs_key_index = -1
        elif join_var_1 in input_variables_map:
            lhs_key_index = input_variables_map.get(join_var_1).index
        else:
            raise RbqlParsingError('Unable to parse JOIN expression: Input table does not have field "{}"\n{}'.format(join_var_1, valid_join_syntax_msg)) # UT JSON
        if join_var_2 in ['bNR', 'b.NR']:
            rhs_key_index = -1
        elif join_var_2 in join_variables_map:
            rhs_key_index = join_variables_map.get(join_var_2).index
        else:
            raise RbqlParsingError('Unable to parse JOIN expression: Join table does not have field "{}"\n{}'.format(join_var_2, valid_join_syntax_msg)) # UT JSON
        lhs_join_var_expression = 'NR' if lhs_key_index == -1 else 'safe_join_get(record_a, {})'.format(lhs_key_index)
        rhs_indices.append(rhs_key_index)
        lhs_variables.append(lhs_join_var_expression)
    return (lhs_variables, rhs_indices)


def parse_basic_variables(query_text, prefix, dst_variables_map):
    assert prefix in ['a', 'b']
    rgx = '(?:^|[^_a-zA-Z0-9]){}([1-9][0-9]*)(?:$|(?=[^_a-zA-Z0-9]))'.format(prefix)
    matches = list(re.finditer(rgx, query_text))
    field_nums = list(set([int(m.group(1)) for m in matches]))
    for field_num in field_nums:
        dst_variables_map[prefix + str(field_num)] = VariableInfo(initialize=True, index=field_num - 1)


def parse_array_variables(query_text, prefix, dst_variables_map):
    assert prefix in ['a', 'b']
    rgx = r'(?:^|[^_a-zA-Z0-9]){}\[([1-9][0-9]*)\]'.format(prefix)
    matches = list(re.finditer(rgx, query_text))
    field_nums = list(set([int(m.group(1)) for m in matches]))
    for field_num in field_nums:
        dst_variables_map['{}[{}]'.format(prefix, field_num)] = VariableInfo(initialize=True, index=field_num - 1)


def python_string_escape_column_name(column_name, quote_char):
    assert quote_char in ['"', "'"]
    column_name = column_name.replace('\\', '\\\\')
    column_name = column_name.replace('\n', '\\n')
    column_name = column_name.replace('\r', '\\r')
    column_name = column_name.replace('\t', '\\t')
    if quote_char == '"':
        return column_name.replace('"', '\\"')
    return column_name.replace("'", "\\'")


def query_probably_has_dictionary_variable(query_text, column_name):
    # It is OK to return false positive - in the worst case we woud just waste some performance on unused variable initialization
    continuous_name_segments = re.findall('[-a-zA-Z0-9_:;+=!.,()%^#@&* ]+', column_name)
    for continuous_segment in continuous_name_segments:
        if query_text.find(continuous_segment) == -1:
            return False
    return True


def parse_dictionary_variables(query_text, prefix, column_names, dst_variables_map):
    # The purpose of this algorithm is to minimize number of variables in varibale_map to improve performance, ideally it should be only variables from the query
    # TODO implement algorithm for honest python f-string parsing
    assert prefix in ['a', 'b']
    if re.search(r'(?:^|[^_a-zA-Z0-9]){}\['.format(prefix), query_text) is None:
        return
    for i in range(len(column_names)):
        column_name = column_names[i]
        if query_probably_has_dictionary_variable(query_text, column_name):
            dst_variables_map['{}["{}"]'.format(prefix, python_string_escape_column_name(column_name, '"'))] = VariableInfo(initialize=True, index=i)
            dst_variables_map["{}['{}']".format(prefix, python_string_escape_column_name(column_name, "'"))] = VariableInfo(initialize=False, index=i)


def parse_attribute_variables(query_text, prefix, column_names, column_names_source, dst_variables_map):
    # The purpose of this algorithm is to minimize number of variables in varibale_map to improve performance, ideally it should be only variables from the query

    # TODO ideally we should either:
    # * not search inside string literals (excluding brackets in f-strings) OR
    # * check if column_name is not among reserved python keywords like "None", "if", "else", etc
    assert prefix in ['a', 'b']
    column_names = {v: i for i, v in enumerate(column_names)}
    rgx = r'(?:^|[^_a-zA-Z0-9]){}\.([_a-zA-Z][_a-zA-Z0-9]*)'.format(prefix)
    matches = list(re.finditer(rgx, query_text))
    column_names_from_query = list(set([m.group(1) for m in matches]))
    for column_name in column_names_from_query:
        zero_based_idx = column_names.get(column_name)
        if zero_based_idx is not None:
            dst_variables_map['{}.{}'.format(prefix, column_name)] = VariableInfo(initialize=True, index=zero_based_idx)
        else:
            raise RbqlParsingError('Unable to find column "{}" in {} {}'.format(column_name, {'a': 'input', 'b': 'join'}[prefix], column_names_source))


def map_variables_directly(query_text, column_names, dst_variables_map):
    for idx, column_name in enumerate(column_names):
        if re.match(r'^[_a-zA-Z][_a-zA-Z0-9]*$', column_name) is None:
            raise RbqlIOHandlingError('Unable to use column name "{}" as RBQL/Python variable'.format(column_name))
        if query_text.find(column_name) != -1:
            dst_variables_map[column_name] = VariableInfo(initialize=True, index=idx)


def ensure_no_ambiguous_variables(query_text, input_column_names, join_column_names):
    join_column_names_set = set(join_column_names)
    for column_name in input_column_names:
        if column_name in join_column_names_set and query_text.find(column_name) != -1: # False positive is tolerable here
            raise RbqlParsingError(ambiguous_error_msg.format(column_name))



def generate_common_init_code(query_text, variable_prefix):
    assert variable_prefix in ['a', 'b']
    result = list()
    result.append('{} = RBQLRecord()'.format(variable_prefix))
    base_var = 'NR' if variable_prefix == 'a' else 'bNR'
    attr_var = '{}.NR'.format(variable_prefix)
    if query_text.find(attr_var) != -1:
        result.append('{} = {}'.format(attr_var, base_var))
    if variable_prefix == 'a' and query_text.find('aNR') != -1:
        result.append('aNR = NR')
    return result


def generate_init_statements(query_text, variables_map, join_variables_map):
    code_lines = generate_common_init_code(query_text, 'a')
    for var_name, var_info in variables_map.items():
        if var_info.initialize:
            code_lines.append('{} = safe_get(record_a, {})'.format(var_name, var_info.index))
    if join_variables_map:
        code_lines += generate_common_init_code(query_text, 'b')
        for var_name, var_info in join_variables_map.items():
            if var_info.initialize:
                code_lines.append('{} = safe_get(record_b, {}) if record_b is not None else None'.format(var_name, var_info.index))
    return '\n'.join(code_lines)


def replace_star_count(aggregate_expression):
    return re.sub(r'(^|(?<=,)) *COUNT\( *\* *\) *($|(?=,))', ' COUNT(1)', aggregate_expression, flags=re.IGNORECASE).lstrip(' ')


def replace_star_vars(rbql_expression):
    star_matches = list(re.finditer(r'(?:^|,) *(\*|a\.\*|b\.\*) *(?=$|,)', rbql_expression))
    last_pos = 0
    result = ''
    for match in star_matches:
        star_expression = match.group(1)
        replacement_expression = '] + ' + {'*': 'star_fields', 'a.*': 'record_a', 'b.*': 'record_b'}[star_expression] + ' + ['
        if last_pos < match.start():
            result += rbql_expression[last_pos:match.start()]
        result += replacement_expression
        last_pos = match.end() + 1 # Adding one to skip the lookahead comma
    result += rbql_expression[last_pos:]
    return result


def translate_update_expression(update_expression, input_variables_map, string_literals):
    assignment_looking_rgx = re.compile(r'(?:^|,) *(a[.#a-zA-Z0-9\[\]_]*) *=(?=[^=])')
    update_expressions = []
    pos = 0
    first_assignment_error = 'Unable to parse "UPDATE" expression: the expression must start with assignment, but "{}" does not look like an assignable field name'.format(update_expression.split('=')[0].strip())
    while True:
        match = assignment_looking_rgx.search(update_expression, pos)
        if not len(update_expressions) and (match is None or match.start() != 0):
            raise RbqlParsingError(first_assignment_error) # UT JSON
        if match is None:
            update_expressions[-1] += update_expression[pos:].strip() + ')'
            break
        if len(update_expressions):
            update_expressions[-1] += update_expression[pos:match.start()].strip() + ')'
        dst_var_name = combine_string_literals(match.group(1).strip(), string_literals)
        var_info = input_variables_map.get(dst_var_name)
        if var_info is None:
            raise RbqlParsingError('Unable to parse "UPDATE" expression: Unknown field name: "{}"'.format(dst_var_name)) # UT JSON
        update_expressions.append('safe_set(up_fields, {}, '.format(var_info.index))
        pos = match.end()
    return combine_string_literals('\n'.join(update_expressions), string_literals)


def translate_select_expression_py(select_expression):
    translated = replace_star_count(select_expression)
    translated = replace_star_vars(translated)
    translated = translated.strip()
    if not len(translated):
        raise RbqlParsingError('"SELECT" expression is empty') # UT JSON
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
        format_parts.append('###RBQL_STRING_LITERAL{}###'.format(literal_id))
        idx_before = m.end()
    format_parts.append(rbql_expression[idx_before:])
    format_expression = ''.join(format_parts)
    format_expression = format_expression.replace('\t', ' ')
    return (format_expression, string_literals)


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
                raise RbqlParsingError('More than one "{}" statements found'.format(statement)) # UT JSON
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
                raise RbqlParsingError('UPDATE keyword must be at the beginning of the query') # UT JSON
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
                raise RbqlParsingError('SELECT keyword must be at the beginning of the query') # UT JSON
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
        raise RbqlParsingError('Query must contain either SELECT or UPDATE statement') # UT JSON
    assert (SELECT in result) != (UPDATE in result)
    return result


def find_top(rb_actions):
    if LIMIT in rb_actions:
        try:
            return int(rb_actions[LIMIT]['text'])
        except ValueError:
            raise RbqlParsingError('LIMIT keyword must be followed by an integer') # UT JSON
    return rb_actions[SELECT].get('top', None)


def translate_except_expression(except_expression, input_variables_map, string_literals):
    skip_vars = except_expression.split(',')
    skip_vars = [v.strip() for v in skip_vars]
    skip_indices = list()
    for var_name in skip_vars:
        var_name = combine_string_literals(var_name, string_literals)
        var_info = input_variables_map.get(var_name)
        if var_info is None:
            raise RbqlParsingError('Unknown field in EXCEPT expression: "{}"'.format(var_name)) # UT JSON
        skip_indices.append(var_info.index)
    skip_indices = sorted(skip_indices)
    skip_indices = [str(v) for v in skip_indices]
    return 'select_except(record_a, [{}])'.format(','.join(skip_indices))


class HashJoinMap:
    # Other possible flavors: BinarySearchJoinMap, MergeJoinMap
    def __init__(self, record_iterator, key_indices):
        self.max_record_len = 0
        self.hash_map = defaultdict(list)
        self.record_iterator = record_iterator
        self.key_indices = None
        self.key_index = None
        if len(key_indices) == 1:
            self.key_index = key_indices[0]
            self.polymorphic_get_key = self.get_single_key
        else:
            self.key_indices = key_indices
            self.polymorphic_get_key = self.get_multi_key


    def get_single_key(self, nr, fields):
        if self.key_index >= len(fields):
            raise RbqlRuntimeError('No field with index {} at record {} in "B" table'.format(self.key_index + 1, nr))
        return nr if self.key_index == -1 else fields[self.key_index]


    def get_multi_key(self, nr, fields):
        result = []
        for ki in self.key_indices:
            if ki >= len(fields):
                raise RbqlRuntimeError('No field with index {} at record {} in "B" table'.format(ki + 1, nr))
            result.append(nr if ki == -1 else fields[ki])
        return tuple(result)


    def build(self):
        nr = 0
        while True:
            fields = self.record_iterator.get_record()
            if fields is None:
                break
            nr += 1
            nf = len(fields)
            self.max_record_len = builtin_max(self.max_record_len, nf)
            key = self.polymorphic_get_key(nr, fields)
            self.hash_map[key].append((nr, nf, fields))


    def get_join_records(self, key):
        return self.hash_map[key]


    def get_warnings(self):
        return self.record_iterator.get_warnings()


def cleanup_query(query_text):
    rbql_lines = query_text.split('\n')
    rbql_lines = [strip_comments(l) for l in rbql_lines]
    rbql_lines = [l for l in rbql_lines if len(l)]
    return ' '.join(rbql_lines)


def remove_redundant_input_table_name(query_text):
    query_text = re.sub(' +from +a(?: +|$)', ' ', query_text, flags=re.IGNORECASE).strip()
    query_text = re.sub('^ *update +a +set ', 'update ', query_text, flags=re.IGNORECASE).strip()
    return query_text


def parse_to_py(query_text, input_iterator, join_tables_registry):
    query_text = cleanup_query(query_text)
    format_expression, string_literals = separate_string_literals_py(query_text)
    format_expression = remove_redundant_input_table_name(format_expression)
    input_variables_map = input_iterator.get_variables_map(query_text)

    rb_actions = separate_actions(format_expression)

    if ORDER_BY in rb_actions and UPDATE in rb_actions:
        raise RbqlParsingError('"ORDER BY" is not allowed in "UPDATE" queries') # UT JSON

    if GROUP_BY in rb_actions:
        if ORDER_BY in rb_actions or UPDATE in rb_actions:
            raise RbqlParsingError(invalid_keyword_in_aggregate_query_error_msg) # UT JSON
        query_context.aggregation_key_expression = '({},)'.format(combine_string_literals(rb_actions[GROUP_BY]['text'], string_literals))


    join_variables_map = None
    if JOIN in rb_actions:
        rhs_table_id, variable_pairs = parse_join_expression(rb_actions[JOIN]['text'])
        if join_tables_registry is None:
            raise RbqlParsingError('JOIN operations are not supported by the application') # UT JSON
        join_record_iterator = join_tables_registry.get_iterator_by_table_id(rhs_table_id)
        if join_record_iterator is None:
            raise RbqlParsingError('Unable to find join table: "{}"'.format(rhs_table_id)) # UT JSON CSV
        join_variables_map = join_record_iterator.get_variables_map(query_text)

        lhs_variables, rhs_indices = resolve_join_variables(input_variables_map, join_variables_map, variable_pairs, string_literals)
        joiner_type = {JOIN: InnerJoiner, INNER_JOIN: InnerJoiner, LEFT_JOIN: LeftJoiner, STRICT_LEFT_JOIN: StrictLeftJoiner}[rb_actions[JOIN]['join_subtype']]
        query_context.join_operation = rb_actions[JOIN]['join_subtype']
        query_context.lhs_join_var_expression = lhs_variables[0] if len(lhs_variables) == 1 else '({})'.format(', '.join(lhs_variables))
        query_context.join_map_impl = HashJoinMap(join_record_iterator, rhs_indices)
        query_context.join_map_impl.build()
        query_context.join_map = joiner_type(query_context.join_map_impl)


    if WHERE in rb_actions:
        where_expression = rb_actions[WHERE]['text']
        if re.search(r'[^!=]=[^=]', where_expression) is not None:
            raise RbqlParsingError('Assignments "=" are not allowed in "WHERE" expressions. For equality test use "=="') # UT JSON
        query_context.where_expression = combine_string_literals(where_expression, string_literals)

    query_context.variables_init_code = combine_string_literals(generate_init_statements(format_expression, input_variables_map, join_variables_map), string_literals)


    if UPDATE in rb_actions:
        update_expression = translate_update_expression(rb_actions[UPDATE]['text'], input_variables_map, string_literals)
        query_context.update_expressions = combine_string_literals(update_expression, string_literals)


    if SELECT in rb_actions:
        query_context.top_count = find_top(rb_actions)
        query_context.writer = TopWriter(query_context.writer)
        if 'distinct_count' in rb_actions[SELECT]:
            query_context.writer = UniqCountWriter(query_context.writer)
        elif 'distinct' in rb_actions[SELECT]:
            query_context.writer = UniqWriter(query_context.writer)
        if EXCEPT in rb_actions:
            query_context.select_expression = translate_except_expression(rb_actions[EXCEPT]['text'], input_variables_map, string_literals)
        else:
            select_expression = translate_select_expression_py(rb_actions[SELECT]['text'])
            query_context.select_expression = combine_string_literals(select_expression, string_literals)

    if ORDER_BY in rb_actions:
        query_context.sort_key_expression = '({})'.format(combine_string_literals(rb_actions[ORDER_BY]['text'], string_literals))
        query_context.reverse_sort = rb_actions[ORDER_BY]['reverse']
        query_context.writer = SortedWriter(query_context.writer)


def make_inconsistent_num_fields_warning(table_name, inconsistent_records_info):
    assert len(inconsistent_records_info) > 1
    inconsistent_records_info = inconsistent_records_info.items()
    inconsistent_records_info = sorted(inconsistent_records_info, key=lambda v: v[1])
    num_fields_1, record_num_1 = inconsistent_records_info[0]
    num_fields_2, record_num_2 = inconsistent_records_info[1]
    warn_msg = 'Number of fields in "{}" table is not consistent: '.format(table_name)
    warn_msg += 'e.g. record {} -> {} fields, record {} -> {} fields'.format(record_num_1, num_fields_1, record_num_2, num_fields_2)
    return warn_msg


def query(query_text, input_iterator, output_writer, output_warnings, join_tables_registry=None, user_init_code=''):
    global query_context
    query_context = RBQLContext(input_iterator, output_writer, user_init_code)
    parse_to_py(query_text, input_iterator, join_tables_registry)
    compile_and_run()
    query_context.writer.finish()
    output_warnings.extend(input_iterator.get_warnings())
    if query_context.join_map_impl is not None:
        output_warnings.extend(query_context.join_map_impl.get_warnings())
    output_warnings.extend(output_writer.get_warnings())


class TableIterator:
    def __init__(self, table, column_names=None, normalize_column_names=True, variable_prefix='a'):
        self.table = table
        self.column_names = column_names
        self.normalize_column_names = normalize_column_names
        self.variable_prefix = variable_prefix
        self.NR = 0
        self.fields_info = dict()

    def get_variables_map(self, query_text):
        variable_map = dict()
        parse_basic_variables(query_text, self.variable_prefix, variable_map)
        parse_array_variables(query_text, self.variable_prefix, variable_map)
        if self.column_names is not None:
            if len(self.table) and len(self.column_names) != len(self.table[0]):
                raise RbqlIOHandlingError('List of column names and table records have different lengths')
            if self.normalize_column_names:
                parse_dictionary_variables(query_text, self.variable_prefix, self.column_names, variable_map)
                parse_attribute_variables(query_text, self.variable_prefix, self.column_names, 'column names list', variable_map)
            else:
                map_variables_directly(query_text, self.column_names, variable_map)
        return variable_map

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
        return True

    def finish(self):
        pass

    def get_warnings(self):
        return []


class SingleTableRegistry:
    def __init__(self, table, column_names=None, normalize_column_names=True, table_name='B'):
        self.table = table
        self.column_names = column_names
        self.normalize_column_names = normalize_column_names
        self.table_name = table_name

    def get_iterator_by_table_id(self, table_id):
        if table_id != self.table_name:
            raise RbqlParsingError('Unable to find join table: "{}"'.format(table_id)) # UT JSON
        return TableIterator(self.table, self.column_names, self.normalize_column_names, 'b')


def query_table(query_text, input_table, output_table, output_warnings, join_table=None, input_column_names=None, join_column_names=None, normalize_column_names=True, user_init_code=''):
    if not normalize_column_names and input_column_names is not None and join_column_names is not None:
        ensure_no_ambiguous_variables(query_text, input_column_names, join_column_names)
    input_iterator = TableIterator(input_table, input_column_names, normalize_column_names)
    output_writer = TableWriter(output_table)
    join_tables_registry = None if join_table is None else SingleTableRegistry(join_table, join_column_names, normalize_column_names)
    query(query_text, input_iterator, output_writer, output_warnings, join_tables_registry, user_init_code=user_init_code)


def set_debug_mode():
    global debug_mode
    debug_mode = True

