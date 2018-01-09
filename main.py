import sublime
import sublime_plugin

from .rainbow_utils import *


def get_view_delim(view_settings):
    syntax = view_settings.get('syntax')
    if syntax.find('csv.tmLanguage') != -1: 
        return ','
    if syntax.find('tsv.tmLanguage') != -1:
        return '\t'
    return None


def is_rainbow_view(view_settings):
    return get_view_delim(view_settings) is not None


def get_line_text(view, lnum):
    point = view.text_point(lnum, 0)
    line = view.substr(view.line(point))
    return line


def get_file_line_count(view):
    return view.rowcol(view.size())[0] + 1


def guess_document_header(view, delim, policy):
    num_lines = get_file_line_count(view)
    head_count = 10
    sampled_lines = []
    if num_lines <= head_count * 2:
        for lnum in range(1, num_lines):
            sampled_lines.append(get_line_text(view, lnum))
    else:
        for lnum in range(1, head_count):
            sampled_lines.append(get_line_text(view, lnum))
        for lnum in range(num_lines - head_count, num_lines):
            sampled_lines.append(get_line_text(view, lnum))

    while len(sampled_lines) and not len(sampled_lines[-1]):
        sampled_lines.pop()
    if len(sampled_lines) < 10:
        return None
    sampled_records = [smart_split(l, delim, policy, False)[0] for l in sampled_lines]
    potential_header = smart_split(get_line_text(view, 0), delim, policy, False)[0]
    has_header = guess_if_header(potential_header, sampled_records)
    return potential_header if has_header else None
        

class ViewRainbowEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return is_rainbow_view(settings)

    def on_hover(self, point, hover_zone):
        if hover_zone == sublime.HOVER_TEXT:
            delim = get_view_delim(self.view.settings())
            policy = 'quoted' if delim == ',' else 'simple'
            # lnum and cnum are 0-based
            lnum, cnum = self.view.rowcol(point)
            line_text = self.view.substr(self.view.line(point))
            hover_record, warning = smart_split(line_text, delim, policy, True)
            if warning or not len(hover_record):
                return
            field_num = get_field_by_line_position(hover_record, cnum)
            header = guess_document_header(self.view, delim, policy)
            ui_text = 'col# {}'.format(field_num + 1)
            if header is not None and len(header) == len(hover_record):
                column_name = header[field_num]
                ui_text += ', "{}"'.format(column_name)
            ui_hex_color = color_entries[field_num % 10][1]
            self.view.show_popup('<span style="color:{}">{}</span>'.format(ui_hex_color, ui_text), sublime.HIDE_ON_MOUSE_MOVE_AWAY, point)
