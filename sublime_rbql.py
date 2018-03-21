import os
import sys
import codecs
import traceback
import subprocess
import tempfile
import time

import rainbow_csv.rbql_core
from rainbow_csv.rbql_core import rbql


def get_random_suffix():
    return str(time.time()).split('.')[0]


def execute_python(src_table_path, rainbow_query, input_delim, input_policy, out_delim, out_policy, dst_table_path):
    # Returns tuple: (error_type, error_details, warnings)
    warnings = []
    csv_encoding = rbql.default_csv_encoding
    with rbql.RbqlPyEnv() as worker_env:
        meta_script_path = worker_env.module_path
        try:
            rbql.parse_to_py([rainbow_query], meta_script_path, input_delim, input_policy, out_delim, out_policy, csv_encoding, None)
        except rbql.RBParsingError as e:
            worker_env.remove_env_dir()
            return ('Parsing Error', str(e), warnings)
        try:
            rbconvert = worker_env.import_worker()
            warnings = None
            with codecs.open(src_table_path, encoding=csv_encoding) as src, codecs.open(dst_table_path, 'w', encoding=csv_encoding) as dst:
                warnings = rbconvert.rb_transform(src, dst)
            if warnings is not None:
                warnings = rbql.make_warnings_human_readable(warnings)
            worker_env.remove_env_dir()
            return (None, None, warnings)
        except Exception as e:
            error_msg = 'Error: Unable to use generated python module.\n'
            error_msg += 'Original python exception:\n{}\n'.format(str(e))
            return ('Execution Error', error_msg, warnings)


def execute_js(src_table_path, rainbow_query, input_delim, input_policy, out_delim, out_policy, dst_table_path):
    # Returns tuple: (error_type, error_details, warnings)
    warnings = []
    csv_encoding = rbql.default_csv_encoding
    tmp_dir = tempfile.gettempdir()
    meta_script_name = 'vim_rb_convert_{}.js'.format(get_random_suffix())
    meta_script_path = os.path.join(tmp_dir, meta_script_name)
    if not rbql.system_has_node_js():
        return ('Execution Error', 'Node.js is not found, test command: "node --version"', warnings)
    try:
        rbql.parse_to_js(src_table_path, dst_table_path, [rainbow_query], meta_script_path, input_delim, input_policy, out_delim, out_policy, csv_encoding, None)
    except rbql.RBParsingError as e:
        return ('Parsing Error', str(e), warnings)
    cmd = ['node', meta_script_path]
    if os.name == 'nt': # Windows
        # Without startupinfo magic Windows will show console window for a longer period.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        pobj = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=si)
    else:
        pobj = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_data, err_data = pobj.communicate()
    error_code = pobj.returncode

    operation_report = rbql.parse_json_report(error_code, err_data)
    operation_error = operation_report.get('error')
    if operation_error is not None:
        return ('Execution Error', operation_error, warnings)
    warnings = operation_report.get('warnings')
    if warnings is not None:
        warnings = rbql.make_warnings_human_readable(warnings)
    rbql.remove_if_possible(meta_script_path)
    return (None, None, warnings)


def converged_execute(meta_language, src_table_path, rainbow_query, input_delim, input_policy, out_delim, out_policy):
    try:
        tmp_dir = tempfile.gettempdir()
        table_name = os.path.basename(src_table_path)
        delim_ext_map = {'\t': '.tsv', ',': '.csv'}
        dst_extension = delim_ext_map[out_delim] if out_delim in delim_ext_map else '.txt'
        dst_table_name = table_name + dst_extension
        dst_table_path = os.path.join(tmp_dir, dst_table_name)
        assert meta_language in ['python', 'js'], 'Meta language must be "python" or "js"'
        if meta_language == 'python':
            exec_result = execute_python(src_table_path, rainbow_query, input_delim, input_policy, out_delim, out_policy, dst_table_path)
        else:
            exec_result = execute_js(src_table_path, rainbow_query, input_delim, input_policy, out_delim, out_policy, dst_table_path)
        error_type, error_details, warnings = exec_result
        if error_type is not None:
            dst_table_path = None
        return (error_type, error_details, warnings, dst_table_path)
    except Exception as e:
        return ('Execution Error', str(e), [], None)


