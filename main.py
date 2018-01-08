import sublime
import sublime_plugin

from .rainbow_utils import *


#def ensure_color_scheme():
#    pass
#    #print("setting color theme")
#    #settings = sublime.load_settings("csv.sublime-settings")
#    #settings.set("color_scheme", "Packages/rainbow_csv/Rainbow.tmTheme")
#    #sublime.save_settings("csv.sublime-settings")
#    #
#    #settings = sublime.load_settings("tsv.sublime-settings")
#    #settings.set("color_scheme", "Packages/rainbow_csv/Rainbow.tmTheme")
#    #sublime.save_settings("tsv.sublime-settings")


#class ExampleCommand(sublime_plugin.TextCommand):
#    def run(self, edit):
#        print("running example command")
#        ensure_color_scheme()


def get_view_delim(view_settings):
    syntax = view_settings.get('syntax')
    if syntax.find('csv.tmLanguage') != -1: 
        return ','
    if syntax.find('tsv.tmLanguage') != -1:
        return '\t'
    return None


def is_rainbow_view(view_settings):
    return get_view_delim(view_settings) is not None


#class RainbowEventListener(sublime_plugin.EventListener):
#    def on_load(self, view):
#        settings = view.settings()
#        if not is_rainbow_view(settings):
#            return
#        print("EventListener on_load triggered")
#        ensure_color_scheme()


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
            fields, warning = smart_split(line_text, delim, policy, True)
            if warning or not len(fields):
                return
            field_num = get_field_by_line_position(fields, cnum)
            ui_field = field_num + 1
            ui_hex_color = color_entries[field_num % 10][1]
            self.view.show_popup('<span style="color:{}">col# {}</span>'.format(ui_hex_color, ui_field), sublime.HIDE_ON_MOUSE_MOVE_AWAY, point)
