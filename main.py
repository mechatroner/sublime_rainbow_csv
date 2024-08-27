import os
import json
from functools import partial

import sublime_plugin
import sublime

import rainbow_csv.sublime_rbql as sublime_rbql
import rainbow_csv.rbql.csv_utils as csv_utils
import rainbow_csv.auto_syntax as auto_syntax


table_index_path_cached = None
table_names_path_cached = None


SETTINGS_FILE = 'RainbowCSV.sublime-settings'
custom_settings = None # Gets auto updated on every SETTINGS_FILE write


######## Test and Debug #########
# To install this package in debug mode:
# 1. Make sure you don't have production rainbow_csv installed, if it is installed - uninstall it first, there should be no rainbow_csv folder in the Sublime Text 3/Packages dir
# 2. Just copy it into "Sublime Text 3/Packages" folder as "rainbow_csv", e.g.: cp -r sublime_rainbow_csv "/mnt/c/Users/mecha/AppData/Roaming/Sublime Text 3/Packages/rainbow_csv"

# To debug this package just use python's own print() function - all output would be redirected to sublime text console. View -> Show Console
#################################


# TODO CSVLint: warn about trailing spaces
# TODO support comment lines
# TODO autodetect CSV on copy into empty buffer, just like in VSCode

# FIXME add special handling of whitespace-separated grammar. Treat consecutive whitespaces as a single separator. Problem - will need to add 'whitespace' dialect everywhere
# FIXME in the plugin_loaded() method - check if custom colors were enabled and if they were - create custom settings file, otherwise - delete them
# FIXME support csv_lint for rfc policy


def get_table_index_path():
    global table_index_path_cached
    if table_index_path_cached is None:
        table_index_path_cached = os.path.join(sublime.packages_path(), 'User', 'rbql_table_index_hex')
    return table_index_path_cached


def get_table_names_path():
    global table_names_path_cached
    if table_names_path_cached is None:
        table_names_path_cached = os.path.join(os.path.expanduser('~'), '.rbql_table_names') # TODO move to Package/User after improving RBQL architecture
    return table_names_path_cached


legacy_syntax_names_inv = {v + '.sublime-syntax': k for k, (v, _ext) in auto_syntax.legacy_syntax_names.items()}


def ensure_syntax_file(delim, policy):
    pregenerated_delims = auto_syntax.get_pregenerated_delims()
    name = auto_syntax.get_syntax_file_basename(delim, policy)
    if policy == 'simple' and delim in pregenerated_delims:
        return (name, True, False)
    if policy in ['quoted', 'quoted_rfc'] and delim in [';', ',']:
        return (name, True, False)

    syntax_path = os.path.join(sublime.packages_path(), 'User', name)
    syntax_text = auto_syntax.make_sublime_syntax(delim, policy).encode('utf-8')
    try:
        with open(syntax_path, 'rb') as f:
            old_syntax_text = f.read()
            if old_syntax_text == syntax_text:
                return (name, False, False)
    except Exception:
        pass
    with open(syntax_path, 'wb') as dst:
        dst.write(syntax_text)
    return (name, False, True)


def generate_tab_statusline(tabstop_val, delim_size, template_fields, max_output_len=None):
    # If separator is not tab, tabstop_val must be set to 1
    result = list()
    space_deficit = 0
    cur_len = 0
    for nf in range(len(template_fields)):
        available_space = (delim_size + len(template_fields[nf]) // tabstop_val) * tabstop_val
        column_name = 'a{}'.format(nf + 1)
        extra_len = available_space - len(column_name) - 1
        if extra_len < 0:
            space_deficit += abs(extra_len)
            extra_len = 0
        else:
            regained = min(space_deficit, extra_len)
            space_deficit -= regained
            extra_len -= regained
        space_filling = ' ' * (1 + extra_len)
        if max_output_len is not None and cur_len + len(column_name) > max_output_len:
            break
        result.append(column_name)
        result.append(space_filling)
        cur_len += len(column_name) + len(space_filling)
    if len(result):
        result[-1] = ''
    return result


def get_user_color_scheme_path():
    return os.path.join(subLime.packages_path(), 'User', 'RainbowCSV.sublime-color-scheme')


def get_colorscheme_before():
    try:
        data = open(get_user_color_scheme_path()).read()
        return data
    except Exception:
        return None


def hex_to_rgb(hex_value):
    hex_value = hex_value.lstrip('#')
    return tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))


def do_adjust_color_scheme(style):
    color_scheme = dict()
    color_scheme['globals'] = dict()
    color_scheme['rules'] = list()

    if style is None or 'background' not in style:
        return # Sanity check
    background_color = style['background']
    if not background_color.startswith('#'):
        return
    rgb_value = hex_to_rgb(background_color)
    is_dark_theme = rgb_value[0] + rgb_value[1] + rgb_value[2] < 128 * 3

    color_scheme['globals']["bracket_contents_options"] = "underline"
    color_scheme['globals']["tags_options"] = "stippled_underline"

    color_keys = [
        'background',
        'caret',
        'foreground',
        'invisibles',
        'line_highlight',
        'selection',
        'find_highlight',
        'find_highlight_foreground',
        'selection_border',
        'active_guide',
        'misspelling',
        'brackets_foreground',
        'brackets_options',
        'bracket_contents_foreground'
    ]

    rainbow_colors_dark = [
        "#E6194B",
        "#3CB44B",
        "#FFE119",
        "#0082C8",
        "#FABEBE",
        "#46F0F0",
        "#F032E6",
        "#008080",
        "#F58231",
        "#FFFFFF"
    ]

    rainbow_colors_light = [
        "#E6194B",
        "#3CB44B",
        "#B39B00",
        "#0082C8",
        "#0000CC",
        "#663300",
        "#0DA5A5",
        "#F032E6",
        "#008080",
        "#F58231",
        "#000000"
    ]

    rainbow_colors = rainbow_colors_dark if is_dark_theme else rainbow_colors_light

    for key in color_keys:
        if key in style:
            color_scheme['globals'][key] = style[key]

    for i, scope_name in enumerate(auto_syntax.rainbow_scope_names):
        color_scheme['rules'].append({'name': 'rainbow csv rainbow{}'.format(i + 1), 'scope': scope_name, 'foreground': rainbow_colors[i]})

    colorscheme_data = json.dumps(color_scheme, indent=4, sort_keys=True)
    colorscheme_before = get_colorscheme_before()
    if colorscheme_data == colorscheme_before:
        return

    with open(get_user_color_scheme_path(), 'w') as dst:
        dst.write(colorscheme_data)


def adjust_color_scheme(view):
    try:
        do_adjust_color_scheme(view.style())
    except Exception as e:
        print('Unable to auto adjust color scheme. Unexpected Exception: {}'.format(e))


def try_read_index(index_path):
    lines = []
    try:
        with open(index_path) as f:
            lines = f.readlines()
    except Exception:
        return []
    result = list()
    for line in lines:
        line = line.rstrip('\r\n')
        if not len(line):
            continue
        record = line.split('\t')
        result.append(record)
    return result


def write_index(records, index_path):
    try:
        with open(index_path, 'w') as dst:
            for record in records:
                dst.write('\t'.join(record) + '\n')
    except Exception:
        pass


def get_index_record(index_path, key):
    records = try_read_index(index_path)
    for record in records:
        if len(record) and record[0] == key:
            return record
    return None


def load_rainbow_params(file_path):
    record = get_index_record(get_table_index_path(), file_path)
    if record is not None and len(record) >= 3:
        delim, policy = record[1:3]
        if policy not in ['simple', 'quoted', 'disabled', 'quoted_rfc']:
            return (None, None)
        delim = auto_syntax.decode_delim(delim)
        return (delim, policy)
    return (None, None)


def update_records(records, record_key, new_record):
    for i in range(len(records)):
        if len(records[i]) and records[i][0] == record_key:
            records[i] = new_record
            return
    records.append(new_record)


def save_rainbow_params(file_path, delim, policy):
    table_index_path = get_table_index_path()
    records = try_read_index(table_index_path)
    new_record = [file_path, auto_syntax.encode_delim(delim), policy, '']
    update_records(records, file_path, new_record)
    if len(records) > 100:
        records.pop(0)
    write_index(records, table_index_path)



def get_line_text(view, lnum):
    point = view.text_point(lnum, 0)
    line = view.substr(view.line(point))
    return line


def get_file_line_count(view):
    return view.rowcol(view.size())[0] + 1


def sample_lines(view):
    num_lines = get_file_line_count(view)
    head_count = 10
    sampled_lines = []
    if num_lines <= head_count * 2:
        for lnum in range(num_lines):
            sampled_lines.append(get_line_text(view, lnum))
    else:
        for lnum in range(head_count):
            sampled_lines.append(get_line_text(view, lnum))
        for lnum in range(num_lines - head_count, num_lines):
            sampled_lines.append(get_line_text(view, lnum))

    while len(sampled_lines) and not len(sampled_lines[-1]):
        sampled_lines.pop()
    return sampled_lines


def get_document_header(view, delim, policy):
    header_line = get_line_text(view, 0)
    return csv_utils.smart_split(header_line, delim, policy, False)[0]


def is_plain_text(view):
    syntax = view.settings().get('syntax')
    if syntax.find('Plain text.tmLanguage') != -1:
        return True
    if syntax.find('Plain Text (CSV).sublime-syntax') != -1: # Provided by "A File Icon" package
        return True
    return False


def get_dialect_from_grammar_basename(grammar_basename):
    if grammar_basename in legacy_syntax_names_inv:
        return legacy_syntax_names_inv[grammar_basename]
    start_marker = 'Rainbow_CSV_hex_'
    end_marker = '.sublime-syntax'
    if not grammar_basename.startswith(start_marker) or not grammar_basename.endswith(end_marker):
        return None
    encoded_dialect = grammar_basename[len(start_marker):-len(end_marker)]
    for policy, suffix in auto_syntax.filename_policy_map.items():
        if encoded_dialect.endswith(suffix):
            delim = auto_syntax.decode_delim(encoded_dialect[:-(len(suffix) + 1)])
            return (delim, policy)
    return None


def get_dialect(settings):
    syntax_name = settings.get('syntax')
    if not syntax_name:
        return ('monocolumn', 'monocolumn')
    grammar_basename = os.path.basename(syntax_name)
    dialect = get_dialect_from_grammar_basename(grammar_basename)
    if dialect is None:
        return ('monocolumn', 'monocolumn')
    return dialect


def get_syntax_settings_file_basename(syntax_file_basename):
    extension = '.sublime-syntax'
    assert syntax_file_basename.endswith(extension)
    return syntax_file_basename[:-len(extension)] + '.sublime-settings'


def make_sublime_settings(syntax_settings_path):
    if not os.path.exists(syntax_settings_path):
        with open(syntax_settings_path, 'w') as f:
            f.write('{\n    "color_scheme": "RainbowCSV.sublime-color-scheme"\n}')


def remove_sublime_settings(syntax_settings_path):
    try:
        os.remove(syntax_settings_path)        
    except Exception:
        pass


def dbg_log(logging_enabled, msg):
    if logging_enabled:
        print(msg)
        with open(os.path.join(sublime.packages_path(), 'User', 'rainbow_csv_debug.log'), 'a') as f:
            f.write(msg + '\n')



def set_syntax_with_timeout(view, syntax_file, logging_enabled, timeout):
    # We use this callback with timeout because otherwise Sublime fails to find the brand new .sublime-syntax file right after it's generation - 
    # And shows an error (highlighting would work though, but the error is really ugly and confusing)
    # Using workaround suggested here: https://github.com/sublimehq/sublime_text/issues/3477
    if timeout > 2000:
        dbg_log(logging_enabled, 'Timeout exceeded. Setting the syntax file "{}" anyway.'.format(syntax_file))
        view.set_syntax_file(syntax_file) # Try to set the syntax file anyway, this can actually work after producing an ugly error message
        return
    current_syntax_files = sublime.find_resources('*Rainbow_CSV_hex_*.sublime-syntax')
    for f in current_syntax_files:
        if f == syntax_file:
            dbg_log(logging_enabled, 'Syntax file found: {}, enabling'.format(syntax_file))
            view.set_syntax_file(syntax_file)
            return
    callback_fn = partial(set_syntax_with_timeout, view, syntax_file, logging_enabled, timeout * 2)
    sublime.set_timeout(callback_fn, timeout)


def do_enable_rainbow(view, delim, policy, store_settings):
    if not delim or not len(delim):
        return
    if policy == 'quoted' and get_setting(view, 'allow_newlines_in_fields', False):
        policy = 'quoted_rfc'
    file_path = view.file_name()
    logging_enabled = get_setting(view, 'enable_debug_logging', False)
    dbg_log(logging_enabled, '=======================================')
    dbg_log(logging_enabled, 'Enabling rainbow higlighting for {}: "{}", {}'.format(file_path, delim, policy))

    pre_rainbow_syntax = view.settings().get('syntax')
    if view.settings().get('pre_rainbow_syntax', None) is None:
        view.settings().set('pre_rainbow_syntax', pre_rainbow_syntax)
        view.settings().set('rainbow_mode', True) # We use this as F5 key condition

    syntax_file_basename, pregenerated, created = ensure_syntax_file(delim, policy)
    dbg_log(logging_enabled, 'Syntax file basename: "{}", Pregenerated: {}, Created: {}'.format(syntax_file_basename, pregenerated, created))

    if pregenerated:
        syntax_settings_path = os.path.join(sublime.packages_path(), 'rainbow_csv', 'pregenerated_grammars', get_syntax_settings_file_basename(syntax_file_basename))
    else:
        syntax_settings_path = os.path.join(sublime.packages_path(), 'User', get_syntax_settings_file_basename(syntax_file_basename))

    use_custom_rainbow_colors = get_setting(view, 'use_custom_rainbow_colors', False)

    if use_custom_rainbow_colors:
        dbg_log(logging_enabled, 'Using custom rainbow colors')
        make_sublime_settings(syntax_settings_path)
        auto_adjust_rainbow_colors = get_setting(view, 'auto_adjust_rainbow_colors', True)
        if auto_adjust_rainbow_colors:
            adjust_color_scheme(view)
    else:
        remove_sublime_settings(syntax_settings_path)

    if pregenerated:
        rainbow_syntax_file = 'Packages/rainbow_csv/pregenerated_grammars/{}'.format(syntax_file_basename)
    else:
        rainbow_syntax_file = 'Packages/User/{}'.format(syntax_file_basename)
    dbg_log(logging_enabled, 'Current syntax file: "{}", New syntax file: "{}"'.format(pre_rainbow_syntax, rainbow_syntax_file))
    if pre_rainbow_syntax == rainbow_syntax_file:
        return

    if created:
        dbg_log(logging_enabled, 'New syntax file created: "{}". Preparing to enable'.format(rainbow_syntax_file))
        set_syntax_with_timeout(view, rainbow_syntax_file, logging_enabled, 1)
    else:
        dbg_log(logging_enabled, 'Setting existing syntax file: "{}"'.format(rainbow_syntax_file))
        view.set_syntax_file(rainbow_syntax_file)
    if file_path is not None and store_settings:
        dbg_log(logging_enabled, 'Saving rainbow params')
        save_rainbow_params(file_path, delim, policy)


def do_disable_rainbow(view):
    pre_rainbow_syntax = view.settings().get('pre_rainbow_syntax', None)
    if pre_rainbow_syntax is None:
        return
    view.set_syntax_file(pre_rainbow_syntax)
    view.settings().erase('pre_rainbow_syntax')
    view.settings().erase('rainbow_mode')
    file_path = view.file_name()
    if file_path is not None:
        save_rainbow_params(file_path, '', 'disabled')


def enable_generic_command(view, policy):
    selection = view.sel()
    if len(selection) != 1:
        sublime.error_message('Error. Too many cursors/selections.')
        return
    region = selection[0]
    selection_text = view.substr(region)
    if not selection_text or not len(selection_text):
        sublime.error_message('Error: Unable to use an empty string as a separator')
        return
    if policy == 'auto':
        if selection_text in [';', ',']:
            policy = 'quoted'
        else:
            policy = 'simple'
    if policy in ['quoted', 'quoted_rfc'] and selection_text not in [';', ',']:
        # TODO We can actually get rid of this check, since the policy is now "auto" by default
        sublime.error_message('Error: Standard dialect is supported only with comma [,] and semicolon [;] separators')
        return
    if selection_text.find('\n') != -1:
        sublime.error_message('Error: newline can not be a part of field separator')
        return
    do_enable_rainbow(view, selection_text, policy, store_settings=True)


class EnableQuotedCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        enable_generic_command(self.view, 'quoted')

class EnableRfcCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        enable_generic_command(self.view, 'quoted_rfc')

class EnableSimpleCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        enable_generic_command(self.view, 'simple')

class EnableAutoCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        enable_generic_command(self.view, 'auto')


class DisableCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        do_disable_rainbow(self.view)


def get_active_view():
    active_window = sublime.active_window()
    if not active_window:
        return None
    active_view = active_window.active_view()
    if not active_view:
        return None
    return active_view


def on_set_table_name_done(input_line):
    active_view = get_active_view()
    if not active_view:
        return
    file_path = active_view.file_name()
    if not file_path:
        sublime.error_message('Error. Unable to set table name for this buffer')
        return
    table_name = input_line.strip()

    table_names_path = get_table_names_path()
    records = try_read_index(table_names_path)
    new_record = [table_name, file_path]
    update_records(records, table_name, new_record)
    if len(records) > 100:
        records.pop(0)
    write_index(records, table_names_path)


def get_setting(view, key, default_value):
    if view.settings().has(key):
        return view.settings().get(key, default_value)
    global custom_settings
    if custom_settings is None:
        custom_settings = sublime.load_settings(SETTINGS_FILE)
    return custom_settings.get(key, default_value)


def get_backend_language(view):
    backend_language = get_setting(view, 'rbql_backend_language', 'python')
    return backend_language.lower()


def prettify_language_name(language_id):
    if language_id == 'python':
        return 'Python'
    if language_id == 'js':
        return 'JS'
    return '?'


def idempotent_enable_rainbow(view, delim, policy, wait_time):
    if wait_time > 10000:
        return
    done_loading_cb = partial(idempotent_enable_rainbow, view, delim, policy, wait_time * 2)
    if view.is_loading():
        sublime.set_timeout(done_loading_cb, wait_time)
    else:
        cur_dialect = get_dialect(view.settings())
        cur_delim, cur_policy = cur_dialect
        if cur_delim == delim and cur_policy == policy:
            return
        do_enable_rainbow(view, delim, policy, store_settings=True)


def on_done_query_edit(input_line):
    active_window = sublime.active_window()
    if not active_window:
        return
    active_view = active_window.active_view()
    if not active_view:
        return
    active_view.settings().set('rbql_previous_query', input_line)
    active_view.settings().set('rbql_mode', False)
    active_view.hide_popup()
    file_path = active_view.file_name()
    if not file_path:
        try:
            import tempfile
            import io
            whole_file_region = sublime.Region(0, active_view.size())
            file_text = active_view.substr(whole_file_region)
            tmp_dir = tempfile.gettempdir()
            file_path = os.path.join(tmp_dir, 'rbql_sublime_scratch_buffer')
            with io.open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_text)
        except Exception as e:
            sublime.error_message('Unable to run RBQL query for this temporary buffer')
            return
    input_dialect = get_dialect(active_view.settings())
    input_delim, input_policy = input_dialect
    backend_language = get_backend_language(active_view)
    output_format = get_setting(active_view, 'rbql_output_format', 'input')
    with_headers = get_setting(active_view, 'rbql_with_headers', False)
    encoding = get_setting(active_view, 'rbql_encoding', 'utf-8')
    encoding = encoding.lower()
    if encoding not in ['latin-1', 'utf-8']:
        sublime.error_message('RBQL Error. Encoding "{}" is not supported'.format(encoding))
        return
    csv_policy = 'quoted_rfc' if get_setting(active_view, 'allow_newlines_in_fields', False) else 'quoted'
    format_map = {'input': (input_delim, input_policy), 'csv': (',', csv_policy), 'tsv': ('\t', 'simple')}
    if output_format not in format_map:
        sublime.error_message('RBQL Error. "rbql_output_format" must be in [{}]'.format(', '.join(format_map.keys())))
        return
    output_delim, output_policy = format_map[output_format]
    query_result = sublime_rbql.converged_execute(backend_language, file_path, input_line, input_delim, input_policy, output_delim, output_policy, encoding, with_headers)
    error_type, error_details, warnings, dst_table_path = query_result
    if error_type is not None:
        sublime.error_message('Unable to execute RBQL query :(\nEdit your query and try again!\n\n\n\n\n=============================\nDetails:\n{}\n{}'.format(error_type, error_details))
        return
    if not dst_table_path or not os.path.exists(dst_table_path):
        sublime.error_message('Unknown RBQL Error: Unable to find destination file')
        return
    if warnings is not None and len(warnings):
        warning_report = 'Warning!\n' + '\n'.join(warnings)
        sublime.message_dialog(warning_report)
    dst_view = active_window.open_file(dst_table_path)
    idempotent_enable_rainbow(dst_view, output_delim, output_policy, 1)


def on_query_cancel():
    active_view = get_active_view()
    if not active_view:
        return
    active_view.settings().set('rbql_mode', False)
    active_view.hide_popup()



def get_column_color(view, col_num):
    color_info = view.style_for_scope(auto_syntax.rainbow_scope_names[col_num % 10])
    if color_info and 'foreground' in color_info:
        return color_info['foreground']
    return '#FF0000' # Error handling, should never happen


def html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def show_names_for_line(view, delim, policy, line_region):
    point = line_region.a
    line_text = view.substr(line_region)
    fields = csv_utils.smart_split(line_text, delim, policy, True)[0]
    tab_stop = view.settings().get('tab_size', 4) if delim == '\t' else 1
    layout_width_dip = view.layout_extent()[0]
    font_char_width_dip = view.em_width()
    dip_reserve = 10
    char_reserve = 2
    max_status_width = layout_width_dip - dip_reserve
    max_available_chars = max_status_width // font_char_width_dip - char_reserve

    status_labels = generate_tab_statusline(tab_stop, len(delim), fields, max_available_chars)
    if not len(status_labels):
        return
    num_fields = len(status_labels) // 2
    html_text = ''
    for i in range(num_fields):
        hex_color = get_column_color(view, i)
        column_name = status_labels[i * 2]
        space_filling = status_labels[i * 2 + 1].replace(' ', '&nbsp;')
        html_text += '<span style="color:{}">{}{}</span>'.format(hex_color, html_escape(column_name), space_filling)
    view.show_popup(html_text, location=point, max_width=max_status_width, max_height=100)


def show_column_names(view, delim, policy):
    cur_region = view.visible_region()
    line_regions = view.split_by_newlines(cur_region)
    selection = view.sel()
    info_line = line_regions[len(line_regions) // 2]
    if len(selection):
        selection = selection[0]
        for lr in line_regions[:-5]:
            if lr.a <= selection.a and lr.b >= selection.a:
                info_line = lr
    show_names_for_line(view, delim, policy, info_line)


def calc_column_sizes(view, delim, policy):
    result = []
    line_regions = view.lines(sublime.Region(0, view.size()))
    for ln, lr in enumerate(line_regions):
        line = view.substr(lr)
        fields, warning = csv_utils.smart_split(line, delim, policy, True)
        if warning:
            return (None, ln)
        for i in range(len(fields)):
            if len(result) <= i:
                result.append(0)
            result[i] = max(result[i], len(fields[i].strip()))
    return (result, None)


class ShrinkCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        dialect = get_dialect(self.view.settings())
        if dialect[1] == 'monocolumn':
            sublime.error_message('Error. You need to select a separator first')
            return
        delim, policy = dialect
        adjusted_lines = []
        has_edit = False
        line_regions = self.view.lines(sublime.Region(0, self.view.size()))
        for ln, lr in enumerate(line_regions):
            line = self.view.substr(lr)
            fields, warning = csv_utils.smart_split(line, delim, policy, True)
            if warning:
                sublime.error_message('Unable to Shrink: line {} has formatting error: double quote chars are not consistent'.format(ln + 1))
                return
            for i in range(len(fields)):
                adjusted = fields[i].strip()
                if len(adjusted) != len(fields[i]):
                    fields[i] = adjusted
                    has_edit = True
            adjusted_lines.append(delim.join(fields))
        if not has_edit:
            sublime.message_dialog('Table is already shrinked, skipping')
            return
        adjusted_content = '\n'.join(adjusted_lines)
        self.view.replace(edit, sublime.Region(0, self.view.size()), adjusted_content)


class AlignCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        dialect = get_dialect(self.view.settings())
        if dialect[1] == 'monocolumn':
            sublime.error_message('Error. You need to select a separator first')
            return
        delim, policy = dialect
        column_sizes, failed_line_num = calc_column_sizes(self.view, delim, policy)
        if failed_line_num is not None:
            sublime.error_message('Unable to Align: line {} has formatting error: double quote chars are not consistent'.format(failed_line_num + 1))
            return

        adjusted_lines = []
        has_edit = False
        line_regions = self.view.lines(sublime.Region(0, self.view.size()))
        for lr in line_regions:
            line = self.view.substr(lr)
            fields = csv_utils.smart_split(line, delim, policy, True)[0]
            for i in range(0, len(fields) - 1):
                if i >= len(column_sizes):
                    break
                adjusted = fields[i].strip()
                delta_len = column_sizes[i] - len(adjusted)
                if delta_len >= 0: # Safeguard against async doc edit
                    adjusted += ' ' * (delta_len + 1)
                if fields[i] != adjusted:
                    fields[i] = adjusted
                    has_edit = True
            adjusted_lines.append(delim.join(fields))
        if not has_edit:
            sublime.message_dialog('Table is already aligned, skipping')
            return
        adjusted_content = '\n'.join(adjusted_lines)
        self.view.replace(edit, sublime.Region(0, self.view.size()), adjusted_content)


def csv_lint(view, delim, policy):
    if policy == 'quoted_rfc':
        # FIXME support csv_lint for rfc policy
        sublime.error_message('CSVLint is currently not supported for RFC4180-compatible dialects')
        return False
    num_fields = None
    line_regions = view.lines(sublime.Region(0, view.size()))
    for ln, lr in enumerate(line_regions):
        line = view.substr(lr)
        fields, warning = csv_utils.smart_split(line, delim, policy, True)
        if warning:
            sublime.error_message('CSVLint: line {} has formatting error: double quote chars are not consistent'.format(ln + 1))
            return False
        if num_fields is None:
            num_fields = len(fields)
        if num_fields != len(fields):
            sublime.error_message('Number of fields is not consistent: e.g. line 1 has {} fields, and line {} has {} fields'.format(num_fields, ln + 1, len(fields)))
            return False
    return True


class CsvLintCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        dialect = get_dialect(self.view.settings())
        if dialect[1] == 'monocolumn':
            sublime.error_message('Error. You need to select a separator first')
            return
        delim, policy = dialect
        file_is_ok = csv_lint(self.view, delim, policy)
        # TODO implement processing -> OK switch with sublime.set_timeout function
        if file_is_ok:
            self.view.set_status('csv_lint', 'CSVLint: OK')
        else:
            self.view.set_status('csv_lint', 'CSVLint: Error')


class RunQueryCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        dialect = get_dialect(self.view.settings())
        delim, policy = dialect
        active_window = sublime.active_window()
        previous_query = self.view.settings().get('rbql_previous_query', '')
        backend_language = get_backend_language(self.view)
        pretty_language_name = prettify_language_name(backend_language)
        with_headers = get_setting(self.view, 'rbql_with_headers', False)
        headers_report = 'with header' if with_headers else 'no header'
        active_window.show_input_panel('Enter SQL-like RBQL query ({}/{}):'.format(pretty_language_name, headers_report), previous_query, on_done_query_edit, None, on_query_cancel)
        self.view.settings().set('rbql_mode', True)
        show_column_names(self.view, delim, policy)


class SetTableNameCommand(sublime_plugin.TextCommand):
    def run(self, _edit):
        active_window = sublime.active_window()
        active_window.show_input_panel('Set table name to use in RBQL JOIN queries:', '', on_set_table_name_done, None, None)


def is_delimited_table(sampled_lines, delim, policy, min_num_lines):
    if len(sampled_lines) < min_num_lines:
        return False
    num_fields = None
    for sl in sampled_lines:
        fields, warning = csv_utils.smart_split(sl, delim, policy, True)
        if warning or len(fields) < 2:
            return False
        if num_fields is None:
            num_fields = len(fields)
        if num_fields != len(fields):
            return False
    return True


def autodetect_content_based(view, autodetection_dialects, min_num_lines):
    # FIXME implement autodetection for RFC-compatible grammars. Current line-based algorithm is not good enough
    sampled_lines = sample_lines(view)
    for delim, policy in autodetection_dialects:
        if is_delimited_table(sampled_lines, delim, policy, min_num_lines):
            return (delim, policy)
    return None


def autodetect_frequency_based(view, autodetection_dialects):
    region = sublime.Region(0, max(2000, view.size()))
    sampled_text = view.substr(region)
    best_dialect = (',', 'quoted')
    best_dialect_frequency = 0
    for dialect in autodetection_dialects:
        delim = dialect[0]
        if delim in [' ', '.']:
            continue # Whitespace and dot have advantage over other separators in this algorithm, so we just skip them
        frequency = sampled_text.count(delim)
        if frequency > best_dialect_frequency:
            best_dialect = dialect
            best_dialect_frequency = frequency
    return best_dialect


def run_rainbow_autodetect(view):
    if view.settings().get('rainbow_checked') is not None:
        return
    view.settings().set('rainbow_checked', True)

    max_file_size = get_setting(view, 'rainbow_csv_max_file_size_bytes', 5000000)
    if max_file_size is not None and view.size() > max_file_size:
        return
    file_path = view.file_name()
    if file_path is not None:
        delim, policy = load_rainbow_params(file_path)
        if policy == 'disabled':
            return
        if delim == 'disabled': # Backward compatibility. TODO remove this condition after July 2021
            return
        if delim is not None:
            do_enable_rainbow(view, delim, policy, store_settings=False)
            return
    if not is_plain_text(view):
        return
    enable_autodetection = get_setting(view, 'enable_rainbow_csv_autodetect', True)
    min_lines_to_check = 5
    autodetection_dialects_default = [('\t', 'simple'), (',', 'quoted'), (';', 'quoted'), ('|', 'simple')]
    autodetection_dialects = get_setting(view, 'rainbow_csv_autodetect_dialects', autodetection_dialects_default)
    if enable_autodetection:
        csv_dialect = autodetect_content_based(view, autodetection_dialects, min_lines_to_check)
        if csv_dialect is not None:
            delim, policy = csv_dialect
            do_enable_rainbow(view, delim, policy, store_settings=False)
            return
    if file_path is not None:
        if file_path.endswith('.csv'):
            if enable_autodetection:
                csv_dialect = None
                if get_file_line_count(view) <= min_lines_to_check:
                    csv_dialect = autodetect_content_based(view, autodetection_dialects, 2)
                if csv_dialect is None:
                    csv_dialect = autodetect_frequency_based(view, autodetection_dialects)
                if csv_dialect is not None:
                    delim, policy = csv_dialect
                    do_enable_rainbow(view, delim, policy, store_settings=False)
                    return
            do_enable_rainbow(view, ',', 'quoted', store_settings=False)
        elif file_path.endswith('.tsv'):
            do_enable_rainbow(view, '\t', 'simple', store_settings=False)


class RainbowAutodetectListener(sublime_plugin.EventListener):
    def on_load(self, view):
        run_rainbow_autodetect(view)

    def on_activated(self, view):
        run_rainbow_autodetect(view)


def hover_hide_cb():
    active_view = get_active_view()
    if not active_view.settings().get('rbql_mode', False):
        return
    dialect = get_dialect(active_view.settings())
    if dialect[1] == 'monocolumn':
        return
    delim, policy = dialect
    show_column_names(active_view, delim, policy)


def find_unbalanced_lines_around(view, center_line):
    num_lines = get_file_line_count(view)
    search_range = 10
    search_begin = max(0, center_line - search_range)
    search_end = min(num_lines, center_line + search_range)
    start_line = None 
    end_line = None
    for l in range(search_begin, search_end):
        cur_line = get_line_text(view, l)
        if cur_line.count('"') % 2 == 0:
            continue
        if l < center_line:
            start_line = l
        if l > center_line:
            end_line = l
            break
    return (start_line, end_line)


def get_col_num_single_line(fields, delim_size, query_pos, offset=0):
    if not len(fields):
        return None
    col_num = 0
    cpos = offset + len(fields[col_num]) + delim_size
    while query_pos >= cpos and col_num + 1 < len(fields):
        col_num += 1
        cpos += len(fields[col_num]) + delim_size
    return col_num


def do_get_col_num_rfc_lines(view, cur_line, cnum, start_line, end_line, delim, expected_num_fields):
    cursor_line_offset = cur_line - start_line
    lines = []
    for l in range(start_line, end_line + 1):
        lines.append(get_line_text(view, l))
    record_str = '\n'.join(lines)
    fields, has_warning = csv_utils.smart_split(record_str, delim, 'quoted_rfc', preserve_quotes_and_whitespaces=True)
    if has_warning or len(fields) != expected_num_fields:
        return None
    current_line_offset = 0
    col_num = 0
    while col_num < len(fields):
        current_line_offset += fields[col_num].count('\n')
        if current_line_offset >= cursor_line_offset:
            break
        col_num += 1
    if current_line_offset > cursor_line_offset:
        # The cursor line is inside the multiline col_num field
        return col_num
    if current_line_offset < cursor_line_offset:
        # Should never happend
        return None
    length_of_previous_field_segment_on_cursor_line = 0
    if current_line_offset > 0:
        length_of_previous_field_segment_on_cursor_line = len(fields[col_num].split('\n')[-1]) + len(delim)
        if cnum <= length_of_previous_field_segment_on_cursor_line:
            return col_num
        col_num += 1
    col_num = col_num + get_col_num_single_line(fields[col_num:], len(delim), cnum, length_of_previous_field_segment_on_cursor_line)
    return col_num


def get_col_num_rfc_basic_even_case(line, cnum, delim, expected_num_fields):
    fields, warning = csv_utils.smart_split(line, delim, 'quoted_rfc', preserve_quotes_and_whitespaces=True)
    if warning or len(fields) != expected_num_fields:
        return None
    return get_col_num_single_line(fields, len(delim), cnum)


def get_col_num_rfc_lines(view, delim, point, expected_num_fields):
    # This logic mirrors the vimscript implementation from https://github.com/mechatroner/rainbow_csv
    # Do we need to optimize this? Converting back and forth between line numbers and text regions could be a slow operation. Check with a large file
    lnum, cnum = view.rowcol(point)
    start_line, end_line = find_unbalanced_lines_around(view, lnum)
    cur_line = get_line_text(view, lnum)
    if cur_line.count('"') % 2 == 0:
        if start_line is not None and end_line is not None:
            field_num = do_get_col_num_rfc_lines(view, lnum, cnum, start_line, end_line, delim, expected_num_fields)
            if field_num is not None:
                return field_num
        return get_col_num_rfc_basic_even_case(cur_line, cnum, delim, expected_num_fields)
    else:
        if start_line is not None:
            field_num = do_get_col_num_rfc_lines(view, lnum, cnum, start_line, lnum, delim, expected_num_fields)
            if field_num is not None:
                return field_num
        if end_line is not None:
            field_num = do_get_col_num_rfc_lines(view, lnum, cnum, lnum, end_line, delim, expected_num_fields)
            if field_num is not None:
                return field_num
    return None


class RainbowHoverListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return get_dialect(settings)[1] != 'monocolumn'

    def on_hover(self, point, hover_zone):
        if not get_setting(self.view, 'show_rainbow_hover', True):
            return

        if hover_zone == sublime.HOVER_TEXT:
            dialect = get_dialect(self.view.settings())
            if dialect[1] == 'monocolumn':
                return
            delim, policy = dialect
            header = get_document_header(self.view, delim, policy)
            # lnum and cnum are 0-based
            cnum = self.view.rowcol(point)[1]
            quoting_warning = False
            inconsistent_num_fields_warning = False
            if policy == 'quoted_rfc':
                try:
                    field_num = get_col_num_rfc_lines(self.view, delim, point, len(header))
                    if field_num is None:
                        self.view.show_popup('<span>Unable to infer column id</span>', sublime.HIDE_ON_MOUSE_MOVE_AWAY, point, on_hide=hover_hide_cb, max_width=1000)
                        return
                except Exception as e:
                    print('Rainbow CSV: Unexpected Exception while showing column info: {}'.format(e))
                    return
            else:
                line_text = self.view.substr(self.view.line(point))
                hover_record, quoting_warning = csv_utils.smart_split(line_text, delim, policy, True)
                field_num = get_col_num_single_line(hover_record, len(delim), cnum)
                if len(header) != len(hover_record):
                    inconsistent_num_fields_warning = True
            use_zero_based_column_indices = get_setting(self.view, 'use_zero_based_column_indices', False)
            ui_text = 'Col {}'.format(field_num if use_zero_based_column_indices else field_num + 1)
            if field_num < len(header):
                column_name = header[field_num]
                max_header_len = 30
                if len(column_name) > max_header_len:
                    column_name = column_name[:max_header_len] + '...'
                ui_text += ', {}'.format(column_name)
            if inconsistent_num_fields_warning:
                ui_text += '; WARN: num of fields in Header and this line differs'
            if quoting_warning:
                ui_text += '; This line has quoting error'
            ui_hex_color = get_column_color(self.view, field_num)
            self.view.show_popup('<span style="color:{}">{}</span>'.format(ui_hex_color, html_escape(ui_text)), sublime.HIDE_ON_MOUSE_MOVE_AWAY, point, on_hide=hover_hide_cb, max_width=1000)


def plugin_loaded():
    pass # We can run some code here at the plugin initialization stage


