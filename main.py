import sublime
import sublime_plugin


# colors were taken from here: https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
# TODO: move into a separate script and also use from convert_color_scheme.py
color_entries = list()
color_entries.append(('rainbow1', '#E6194B', None))
color_entries.append(('keyword.rainbow2', '#3CB44B', None))
color_entries.append(('entity.name.rainbow3', '#FFE119', None))
color_entries.append(('comment.rainbow4', '#0082C8', None))
color_entries.append(('string.rainbow5', '#FABEBE', None))
color_entries.append(('entity.name.tag.rainbow6', '#46F0F0', None))
color_entries.append(('storage.type.rainbow7', '#F032E6', None))
color_entries.append(('support.rainbow8', '#008080', None))
color_entries.append(('constant.language.rainbow9', '#F58231', None))
color_entries.append(('variable.language.rainbow10', '#FFFFFF', None))


# taken from rbql_utils.py:
def split_quoted_str(src, dlm, preserve_quotes=False):
    assert dlm != '"'
    if src.find('"') == -1: #optimization for majority of lines
        return (src.split(dlm), False)
    result = list()
    cidx = 0
    while cidx < len(src):
        if src[cidx] == '"':
            uidx = cidx + 1
            while True:
                uidx = src.find('"', uidx)
                if uidx == -1:
                    result.append(src[cidx:])
                    return (result, True)
                elif uidx + 1 == len(src) or src[uidx + 1] == dlm:
                    if preserve_quotes:
                        result.append(src[cidx:uidx + 1])
                    else:
                        result.append(src[cidx + 1:uidx].replace('""', '"'))
                    cidx = uidx + 2
                    break
                elif src[uidx + 1] == '"':
                    uidx += 2
                    continue
                else:
                    result.append(src[cidx:])
                    return (result, True)
        else:
            uidx = src.find(dlm, cidx)
            if uidx == -1:
                uidx = len(src)
            field = src[cidx:uidx]
            if field.find('"') != -1:
                result.append(src[cidx:])
                return (result, True)
            result.append(field)
            cidx = uidx + 1
    if src[-1] == dlm:
        result.append('')
    return (result, False)


def smart_split(src, dlm, policy, preserve_quotes):
    if policy == 'simple':
        return (src.split(dlm), False)
    return split_quoted_str(src, dlm, preserve_quotes)


def get_field_by_line_position(fields, query_pos):
    if not len(fields):
        return None
    col_num = 0
    cpos = len(fields[col_num]) + 1
    while query_pos > cpos and col_num + 1 < len(fields):
        col_num += 1
        cpos = cpos + len(fields[col_num]) + 1
    return col_num


def ensure_color_scheme():
    pass
    #print("setting color theme")
    #settings = sublime.load_settings("csv.sublime-settings")
    #settings.set("color_scheme", "Packages/rainbow_csv/Rainbow.tmTheme")
    #sublime.save_settings("csv.sublime-settings")
    #
    #settings = sublime.load_settings("tsv.sublime-settings")
    #settings.set("color_scheme", "Packages/rainbow_csv/Rainbow.tmTheme")
    #sublime.save_settings("tsv.sublime-settings")


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


class RainbowEventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        settings = view.settings()
        if not is_rainbow_view(settings):
            return
        print("EventListener on_load triggered")
        ensure_color_scheme()


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
