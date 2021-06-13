import os
import sys
import codecs
import traceback
import subprocess
import tempfile
import time

import rainbow_csv.rbql as rbql


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


def execute_python(src_table_path, encoding, query, input_delim, input_policy, out_delim, out_policy, dst_table_path, with_headers):
    try:
        warnings = []
        rbql.query_csv(query, src_table_path, input_delim, input_policy, dst_table_path, out_delim, out_policy, encoding, warnings, with_headers)
        return (None, None, warnings)
    except Exception as e:
        error_type, error_msg = rbql.exception_to_error_info(e)
        return (error_type, error_msg, [])


def execute_js(src_table_path, encoding, query, input_delim, input_policy, out_delim, out_policy, dst_table_path, with_headers):
    import json
    if not system_has_node_js():
        return ('Execution Error', 'Node.js is not found in your OS, test command: "node --version"', [])
    script_dir = os.path.dirname(os.path.realpath(__file__))
    rbql_js_script_path = os.path.join(script_dir, 'rbql-js', 'cli_rbql.js')
    cmd = ['node', rbql_js_script_path, '--query', query, '--delim', input_delim, '--policy', input_policy, '--out-delim', out_delim, '--out-policy', out_policy, '--input', src_table_path, '--output', dst_table_path, '--encoding', encoding, '--error-format', 'json']
    if with_headers:
        cmd.append('--with-headers')
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
            err_data = err_data.decode('utf-8')
            json_err = json.loads(err_data)
            error_type = json_err.get('error_type', None)
            error_msg = json_err.get('error', None)
            warnings = json_err.get('warnings', [])
        except Exception as e:
            error_type = 'Unexpected Error'
            error_msg = 'Unable to parse rbql-js error: {}, report: "{}"'.format(e, err_data)
    if error_type is None and error_code:
        error_type = 'Unexpected Error'
        error_msg = 'rbq-js failed with exit code: {}'.format(error_code)
    return (error_type, error_msg, warnings)


def converged_execute(meta_language, src_table_path, query, input_delim, input_policy, out_delim, out_policy, encoding, with_headers):
    try:
        tmp_dir = tempfile.gettempdir()
        table_name = os.path.basename(src_table_path)
        delim_ext_map = {'\t': '.tsv', ',': '.csv'}
        dst_extension = delim_ext_map[out_delim] if out_delim in delim_ext_map else '.txt'
        dst_table_name = table_name + dst_extension
        dst_table_path = os.path.join(tmp_dir, dst_table_name)
        assert meta_language in ['python', 'js'], 'Meta language must be "python" or "js"'
        if meta_language == 'python':
            exec_result = execute_python(src_table_path, encoding, query, input_delim, input_policy, out_delim, out_policy, dst_table_path, with_headers)
        else:
            exec_result = execute_js(src_table_path, encoding, query, input_delim, input_policy, out_delim, out_policy, dst_table_path, with_headers)
        error_type, error_details, warnings = exec_result
        if error_type is not None:
            dst_table_path = None
        return (error_type, error_details, warnings, dst_table_path)
    except Exception as e:
        return ('Execution Error', str(e), [], None)


