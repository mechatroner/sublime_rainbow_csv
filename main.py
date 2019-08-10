import os
import re
import json
from functools import partial

import sublime_plugin
import sublime

import rainbow_csv.rainbow_utils as rainbow_utils
import rainbow_csv.sublime_rbql as sublime_rbql


table_index_path = None
table_names_path = None

SETTINGS_FILE = 'RainbowCSV.sublime-settings'
custom_settings = None # Gets auto updated on every SETTINGS_FILE write


# To debug this package just use python's own print() function - all output would be redirected to sublime text console. View -> Show Console


# TODO allow monocolumn tables. This could be complicated because we will need to make sure that F5 button would pass context check
# Problem with output format in this case - we don't want to use comma because in 99% output would be single column and comma would make it quoted. the optimal way is "lazy" csv: no quoting when output is single column, otherwise regular csv

# TODO consider implementing syntax with newlines-in-fields support. measure performance.

# TODO CSVLint: warn about trailing spaces
# TODO comments support

# FIXME add CSVLint
# FIXME add Align/Shrink commands
# FIXME improve autodetection algorithm, include pipe
# FIXME switch to new RBQL
# FIXME support multi-character separators


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


naughty_delims_map = {
    '<': 'less-than',
    '>': 'greater-than',
    ':': 'colon',
    '"': 'double-quote',
    '/': 'slash',
    '\\': 'backslash',
    '|': 'pipe',
    '?': 'question-mark',
    '*': 'asterisk',
    '\t': 'tab',
    ' ': 'space'
}


legacy_syntax_names = {
    ('\t', 'simple'): 'TSV (Rainbow).sublime-syntax',
    (',', 'quoted'): 'CSV (Rainbow).sublime-syntax'
}


policy_map = {'simple': 'Simple', 'quoted': 'Standard'}


naughty_delims_map_inv = {v: k for k, v in naughty_delims_map.items()}
legacy_syntax_names_inv = {v: k for k, v in legacy_syntax_names.items()}
policy_map_inv = {v: k for k, v in policy_map.items()}


def init_user_data_paths():
    global table_index_path
    global table_names_path
    if table_index_path is not None and table_names_path is not None:
        return
    user_home_dir = os.path.expanduser('~')
    packages_path = sublime.packages_path()
    sublime_user_dir = os.path.join(packages_path, 'User')
    if os.path.exists(sublime_user_dir):
        table_index_path = os.path.join(sublime_user_dir, 'rbql_table_index')
    else:
        table_index_path = os.path.join(user_home_dir, '.rbql_table_index')
    table_names_path = os.path.join(user_home_dir, '.rbql_table_names') # TODO move to Package/User after improving RBQL architecture


def get_user_color_scheme_path():
    return os.path.join(sublime.packages_path(), 'User', 'RainbowCSV.sublime-color-scheme')


def get_syntax_before():
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

    for i, scope_name in enumerate(rainbow_scope_names): 
        color_scheme['rules'].append({'name': 'rainbow csv rainbow{}'.format(i + 1), 'scope': scope_name, 'foreground': rainbow_colors[i]})

    syntax_data = json.dumps(color_scheme, indent=4, sort_keys=True)
    syntax_data_before = get_syntax_before()
    if syntax_data == syntax_data_before:
        return

    with open(get_user_color_scheme_path(), 'w') as dst:
        dst.write(syntax_data)



def adjust_color_scheme(view):
    try:
        do_adjust_color_scheme(view.style())
    except Exception as e:
        print('Unable to auto adjust color scheme. Unexpected Exception: {}'.format(e))



def index_decode_delim(delim):
    if delim == 'TAB':
        return '\t'
    return delim


def index_encode_delim(delim):
    if delim == '\t':
        return 'TAB'
    return delim


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
    with open(index_path, 'w') as dst:
        for record in records:
            dst.write('\t'.join(record) + '\n')


def get_index_record(index_path, key):
    records = try_read_index(index_path)
    for record in records:
        if len(record) and record[0] == key:
            return record
    return None


def load_rainbow_params(file_path):
    record = get_index_record(table_index_path, file_path)
    if record is not None and len(record) >= 3:
        delim, policy = record[1:3]
        delim = index_decode_delim(delim)
        return (delim, policy)
    return (None, None)


def update_records(records, record_key, new_record):
    for i in range(len(records)):
        if len(records[i]) and records[i][0] == record_key:
            records[i] = new_record
            return
    records.append(new_record)


def save_rainbow_params(file_path, delim, policy):
    records = try_read_index(table_index_path)
    new_record = [file_path, index_encode_delim(delim), policy, '']
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
    return rainbow_utils.smart_split(header_line, delim, policy, False)[0]


def is_plain_text(view):
    syntax = view.settings().get('syntax')
    return syntax.find('Plain text.tmLanguage') != -1


def name_normalize(delim):
    if delim in naughty_delims_map:
        return naughty_delims_map[delim]
    return '[{}]'.format(delim)


def name_normalize_inv(name):
    if name in naughty_delims_map_inv:
        return naughty_delims_map_inv[name]
    if name.startswith('[') and name.endswith(']'):
        return name[1:-1]
    return None


def get_grammar_basename_from_dialect(delim, policy):
    if (delim, policy) in legacy_syntax_names:
        return legacy_syntax_names[(delim, policy)]
    simple_delims = '\t !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    standard_delims = '\t|,;'
    if policy == 'simple' and simple_delims.find(delim) == -1:
        return None
    if policy == 'quoted' and standard_delims.find(delim) == -1:
        return None
    policy_map = {'simple': 'Simple', 'quoted': 'Standard'}
    return 'Rainbow CSV {} {}.sublime-syntax'.format(name_normalize(delim), policy_map[policy])


def get_dialect_from_grammar_basename(grammar_basename):
    if grammar_basename in legacy_syntax_names_inv:
        return legacy_syntax_names_inv[grammar_basename]
    start_marker = 'Rainbow CSV '
    end_marker = '.sublime-syntax'
    if not grammar_basename.startswith(start_marker) or not grammar_basename.endswith(end_marker):
        return None
    encoded_dialect = grammar_basename[len(start_marker):-len(end_marker)]
    wpos = encoded_dialect.rfind(' ')
    if wpos == -1:
        return None
    delim = name_normalize_inv(encoded_dialect[:wpos])
    policy = policy_map_inv.get(encoded_dialect[wpos + 1:], None)
    if delim is None or policy is None:
        return None
    return (delim, policy)


def get_dialect(settings):
    syntax_name = settings.get('syntax')
    if not syntax_name:
        return None
    grammar_basename = os.path.basename(syntax_name)
    return get_dialect_from_grammar_basename(grammar_basename)


def idempotent_enable_rainbow(view, delim, policy, wait_time):
    if wait_time > 10000:
        return
    done_loading_cb = partial(idempotent_enable_rainbow, view, delim, policy, wait_time * 2)
    if view.is_loading():
        sublime.set_timeout(done_loading_cb, wait_time)
    else:
        cur_dialect = get_dialect(view.settings())
        if cur_dialect is None:
            return
        cur_delim, cur_policy = cur_dialect
        if cur_delim == delim and cur_policy == policy:
            return
        do_enable_rainbow(view, delim, policy)


def do_enable_rainbow(view, delim, policy, store_settings=True):
    auto_adjust_rainbow_colors = get_setting(view, 'auto_adjust_rainbow_colors', True)
    if auto_adjust_rainbow_colors:
        adjust_color_scheme(view)
    grammar_basename = get_grammar_basename_from_dialect(delim, policy)
    if grammar_basename is None:
        if policy == 'quoted':
            sublime.error_message('Error: Only "Simple" dialect is available for this character')
        else:
            sublime.error_message('Error: Unable to use this character as a separator')
        return
    if view.settings().get('pre_rainbow_syntax', None) is None:
        pre_rainbow_syntax = view.settings().get('syntax') 
        view.settings().set('pre_rainbow_syntax', pre_rainbow_syntax)
        view.settings().set('rainbow_mode', True) # We use this as F5 key condition
    view.set_syntax_file('Packages/rainbow_csv/custom_grammars/{}'.format(grammar_basename))
    file_path = view.file_name()
    if file_path is not None:
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
        save_rainbow_params(file_path, 'disabled', '')


def enable_generic_command(view, policy):
    selection = view.sel()
    if len(selection) != 1:
        sublime.error_message('Error. Too many cursors/selections.')
        return
    region = selection[0]
    selection_text = view.substr(region)
    if len(selection_text) != 1:
        sublime.error_message('Error. Exactly one separator character should be selected.')
        return
    do_enable_rainbow(view, selection_text, policy)


class EnableStandardCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        enable_generic_command(self.view, 'quoted')


class EnableSimpleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        enable_generic_command(self.view, 'simple')


class DisableCommand(sublime_plugin.TextCommand):
    def run(self, edit):
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


def on_query_done(input_line):
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
        # TODO create a temp file from unnamed buffer
        sublime.error_message('RBQL Error. Unable to run query for this buffer')
        return
    input_dialect = get_dialect(active_view.settings())
    if input_dialect is None:
        sublime.error_message('Unexpected error: Rainbow syntax was just disabled?')
        return
    input_delim, input_policy = input_dialect
    backend_language = get_backend_language(active_view)
    output_format = get_setting(active_view, 'rbql_output_format', 'input')
    format_map = {'input': (input_delim, input_policy), 'csv': (',', 'quoted'), 'tsv': ('\t', 'simple')}
    if output_format not in format_map:
        sublime.error_message('RBQL Error. "rbql_output_format" must be in [{}]'.format(', '.join(format_map.keys())))
        return
    output_delim, output_policy = format_map[output_format]
    query_result = sublime_rbql.converged_execute(backend_language, file_path, input_line, input_delim, input_policy, output_delim, output_policy)
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
    color_info = view.style_for_scope(rainbow_scope_names[col_num % 10])
    if color_info and 'foreground' in color_info:
        return color_info['foreground']
    return '#FF0000' # Error handling, should never happen


def show_names_for_line(view, delim, policy, line_region):
    point = line_region.a
    line_text = view.substr(line_region)
    fields, warning = rainbow_utils.smart_split(line_text, delim, policy, True)
    tab_stop = view.settings().get('tab_size', 4) if delim == '\t' else 1
    layout_width_dip = view.layout_extent()[0]
    font_char_width_dip = view.em_width()
    dip_reserve = 10
    char_reserve = 2
    max_status_width = layout_width_dip - dip_reserve
    max_available_chars = max_status_width // font_char_width_dip - char_reserve

    status_labels = rainbow_utils.generate_tab_statusline(tab_stop, fields, max_available_chars)
    if not len(status_labels):
        return
    num_fields = len(status_labels) // 2
    html_text = ''
    for i in range(num_fields):
        hex_color = get_column_color(view, i)
        column_name = status_labels[i * 2]
        space_filling = status_labels[i * 2 + 1].replace(' ', '&nbsp;')
        html_text += '<span style="color:{}">{}{}</span>'.format(hex_color, column_name, space_filling)
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
        fields, warning = rainbow_utils.smart_split(line, delim, policy, True)
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
        if not dialect:
            sublime.error_message('Error. You need to select a separator first')
            return
        delim, policy = dialect
        adjusted_lines = []
        has_edit = False
        line_regions = self.view.lines(sublime.Region(0, self.view.size()))
        for ln, lr in enumerate(line_regions):
            line = self.view.substr(lr)
            fields, warning = rainbow_utils.smart_split(line, delim, policy, True)
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
        if not dialect:
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
            fields = rainbow_utils.smart_split(line, delim, policy, True)[0]
            for i in range(len(fields)):
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


class RunQueryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        dialect = get_dialect(self.view.settings())
        if not dialect:
            sublime.error_message('Error. You need to select a separator first')
            return
        delim, policy = dialect
        active_window = sublime.active_window()
        previous_query = self.view.settings().get('rbql_previous_query', '')
        backend_language = get_backend_language(self.view)
        pretty_language_name = prettify_language_name(backend_language)
        active_window.show_input_panel('Enter SQL-like RBQL query ({}):'.format(pretty_language_name), previous_query, on_query_done, None, on_query_cancel)
        self.view.settings().set('rbql_mode', True)
        show_column_names(self.view, delim, policy)


class SetTableNameCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        active_window = sublime.active_window()
        active_window.show_input_panel('Set table name to use in RBQL JOIN queries:', '', on_set_table_name_done, None, None)


def is_delimited_table(sampled_lines, delim, policy):
    if len(sampled_lines) < 2:
        return False
    num_fields = None
    for sl in sampled_lines:
        fields, warning = rainbow_utils.smart_split(sl, delim, policy, True)
        if warning or len(fields) < 2:
            return False
        if num_fields is None:
            num_fields = len(fields)
        if num_fields != len(fields):
            return False
    return True


def autodetect_content_based(view):
    sampled_lines = sample_lines(view)
    autodetection_dialects_default = [('\t', 'simple'), (',', 'quoted'), (';', 'quoted')]
    autodetection_dialects = get_setting(view, 'rainbow_csv_autodetect_dialects', autodetection_dialects_default)
    for delim, policy in autodetection_dialects:
        if is_delimited_table(sampled_lines, delim, policy):
            return (delim, policy)
    return None


def run_rainbow_init(view):
    if view.settings().get('rainbow_inited') is not None:
        return
    init_user_data_paths()

    #print('hello world!') # Debug print example
    max_file_size = get_setting(view, 'rainbow_csv_max_file_size_bytes', 5000000)
    if max_file_size is not None and view.size() > max_file_size:
        return
    view.settings().set('rainbow_inited', True)
    file_path = view.file_name()
    if file_path is not None:
        delim, policy = load_rainbow_params(file_path)
        if delim == 'disabled':
            return
        if delim is not None:
            do_enable_rainbow(view, delim, policy, store_settings=False)
            return
    if not is_plain_text(view):
        return
    if get_setting(view, 'enable_rainbow_csv_autodetect', True):
        csv_dialect = autodetect_content_based(view)
        if csv_dialect is not None:
            delim, policy = csv_dialect
            do_enable_rainbow(view, delim, policy, store_settings=False)
            return
    if file_path is not None:
        if file_path.endswith('.csv'):
            do_enable_rainbow(view, ',', 'quoted', store_settings=False)
        elif file_path.endswith('.tsv'):
            do_enable_rainbow(view, '\t', 'simple', store_settings=False)


class RainbowAutodetectListener(sublime_plugin.EventListener):
    def on_load(self, view):
        run_rainbow_init(view)

    def on_activated(self, view):
        run_rainbow_init(view)


def hover_hide_cb():
    active_view = get_active_view()
    if not active_view.settings().get('rbql_mode', False):
        return
    dialect = get_dialect(active_view.settings())
    if not dialect:
        return
    delim, policy = dialect
    show_column_names(active_view, delim, policy)


class RainbowHoverListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return get_dialect(settings) is not None

    def on_hover(self, point, hover_zone):
        if hover_zone == sublime.HOVER_TEXT:
            dialect = get_dialect(self.view.settings())
            if not dialect:
                return
            delim, policy = dialect
            # lnum and cnum are 0-based
            lnum, cnum = self.view.rowcol(point)
            line_text = self.view.substr(self.view.line(point))
            hover_record, warning = rainbow_utils.smart_split(line_text, delim, policy, True)
            field_num = rainbow_utils.get_field_by_line_position(hover_record, cnum)
            header = get_document_header(self.view, delim, policy)
            ui_text = 'Col #{}'.format(field_num + 1)
            if field_num < len(header):
                column_name = header[field_num]
                max_header_len = 30
                if len(column_name) > max_header_len:
                    column_name = column_name[:max_header_len] + '...'
                ui_text += ', Header: "{}"'.format(column_name)
            if len(header) != len(hover_record):
                ui_text += '; WARN: num of fields in Header and this line differs'
            if warning:
                ui_text += '; This line has quoting error'
            ui_hex_color = get_column_color(self.view, field_num)
            self.view.show_popup('<span style="color:{}">{}</span>'.format(ui_hex_color, ui_text), sublime.HIDE_ON_MOUSE_MOVE_AWAY, point, on_hide=hover_hide_cb, max_width=1000)
