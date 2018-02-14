import os
import sublime
import sublime_plugin

from .rainbow_utils import *


def get_view_delim(view_settings):
    syntax = view_settings.get('syntax')
    if syntax.find('CSV (Rainbow).tmLanguage') != -1: 
        return ','
    if syntax.find('TSV (Rainbow).tmLanguage') != -1:
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
        


def is_plain_text(view):
    syntax = view.settings().get('syntax')
    return syntax.find('Text/Plain') != -1


class DisableCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        pass
        print('disabling...')
        #self.view.insert(edit, 0, "Hello, World!")


class EnableStandardCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        pass
        print('enabling standard...')
        #self.view.insert(edit, 0, "Hello, World!")


def name_normalize(delim):
    if delim == '/':
        return 'slash'
    if delim == '\t':
        return 'tab'
    if delim == ' ':
        return 'space'
    return '[{}]'.format(delim)


def get_grammar_basename(delim, policy):
    if delim == '\t' and policy == 'simple':
        return 'TSV (Rainbow)'
    if delim == ',' and policy == 'quoted':
        return 'CSV (Rainbow)'
    simple_delims = ' !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~\t'
    standard_delims = '\t|,;'
    if policy == 'simple' and simple_delims.find(delim) == -1:
        return None
    if policy == 'quoted' and standard_delims.find(delim) == -1:
        return None
    policy_map = {'simple': 'Simple', 'quoted': 'Standard'}
    return 'Rainbow {} {}.tmLanguage'.format(name_normalize(delim), policy_map[policy])



class EnableSimpleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        selection = self.view.sel()
        if len(selection) != 1:
            sublime.error_message('Error. Too many cursors/selections.')
            return
        region = selection[0]
        selection_text = self.view.substr(region)
        if len(selection_text) != 1:
            sublime.error_message('Error. Exactly one separator character should be selected.')
            return
        #print( "selection_text:", selection_text) #FOR_DEBUG
        grammar_basename =  get_grammar_basename(selection_text, 'simple')
        if grammar_basename is None:
            sublime.error_message('Error. Unable to use this character as a separator.')
            return
        self.view.set_syntax_file(os.path.join('Packages', 'rainbow_csv', 'custom_grammars', grammar_basename))
        #self.view.insert(edit, 0, "Hello, World!")


class RainbowAutodetectListener(sublime_plugin.EventListener):
    def on_load(self, view):
        if not is_plain_text(view):
            return
        #FIXME now run autodetection and set the right syntax
        

        #syntax = view.settings().get('syntax')
        #if syntax.find('Text/Plain') == -1:
        #    return
        #print("loaded!")
        #file_path = view.file_name()
        #print( "file_path:", file_path, "\tsyntax:", syntax) #FOR_DEBUG
        ## plain syntaxes:
        ##file_path: /home/snow/university_ranking.txt 	syntax: Packages/Text/Plain text.tmLanguage
        ##file_path: /home/snow/movies.ksv 	syntax: Packages/Text/Plain text.tmLanguage


class RainbowHoverListener(sublime_plugin.ViewEventListener):
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
