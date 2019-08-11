import os
import sys
import codecs
import traceback
import subprocess
import tempfile
import time

import rbql
from rbql import rbql_csv
from rbql import csv_utils


def system_has_node_js():
    exit_code = 0
    out_data = ''
    try:
        cmd = ['node', '--version']
        pobj = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_data, err_data = pobj.communicate()
        exit_code = pobj.returncode
    except OSError as e:
        if e.errno == 2:
            return False
        raise
    return exit_code == 0 and len(out_data) and len(err_data) == 0


def execute_python(src_table_path, rainbow_query, input_delim, input_policy, out_delim, out_policy, dst_table_path):
    csv_encoding = csv_utils.default_csv_encoding
    error_info, warnings = rbql_csv.csv_run(query, src_table_path, input_delim, input_policy, dst_table_path, out_delim, out_policy, csv_encoding)
    if error_info is None:
        return (None, None, warnings)
    else:
        return (error_info['type'], error_info['message'], warnings) 


def execute_js(src_table_path, rainbow_query, input_delim, input_policy, out_delim, out_policy, dst_table_path):
    import json
    if not system_has_node_js():
        return ('Execution Error', 'Node.js is not found in your OS, test command: "node --version"', [])
    script_dir = os.path.dirname(os.path.realpath(__file__))
    encoding = 'binary' # TODO make configurable
    rbql_js_script_path = os.path.join(script_dir, 'rbql-js', 'cli_rbql.js')
    cmd = ['node', rbql_js_script_path, '--query', rainbow_query, '--delim', input_delim, '--policy', input_policy, '--out-delim', out_delim, '--out-policy', out_policy, '--input', src_table_path, '--output', dst_table_path, '--encoding', encoding, '--error-format', 'json']
    if os.name == 'nt':
        # Without the startupinfo magic Windows will show console window for a longer period.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        pobj = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=si)
    else:
        pobj = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_data, err_data = pobj.communicate()
    error_code = pobj.returncode
    error_type = None
    error_msg = None
    warnings = []
    err_data = err_data.strip()
    if len(err_data):
        try:
            json_err = json.loads(err_data)
            error_type = json_err.get('error_type', None)
            error_msg = json_err.get('error_msg', None)
            warnings = json_err.get('warnings', [])
        except Exception as e:
            error_type = 'Unexpected Error'
            error_msg = 'Unable to parse rbql-js error report'
    if error_type is None and error_code:
        error_type = 'Unexpected Error'
        error_msg = 'rbq-js failed with exit code: {}'.format(error_code)
    return (error_type, error_msg, warnings)


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


