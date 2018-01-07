import sublime
import sublime_plugin


# colors were taken from here: https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
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


def ensure_color_scheme():
    print("setting color theme")
    preferences = sublime.load_settings("csv.sublime-settings")
    preferences.set("color_scheme", "Packages/rainbow_csv/Rainbow.tmTheme")
    sublime.save_settings("csv.sublime-settings")

    preferences = sublime.load_settings("tsv.sublime-settings")
    preferences.set("color_scheme", "Packages/rainbow_csv/Rainbow.tmTheme")
    sublime.save_settings("tsv.sublime-settings")


#class ExampleCommand(sublime_plugin.TextCommand):
#    def run(self, edit):
#        print("running example command")
#        ensure_color_scheme()


def is_rainbow_view(view_settings):
    syntax = view_settings.get('syntax')
    return syntax.find('csv.tmLanguage') != -1 or syntax.find('tsv.tmLanguage') != -1


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

    #def on_hover(self, point, hover_zone):
    #    if hover_zone == sublime.HOVER_TEXT:
    #        # FIXME use view.show_popup() instead
    #        self.view.set_status('rainbow_csv_hover', 'hovering!')
    #    else:
    #        self.view.set_status('rainbow_csv_hover', '')
    #    #print("hovering")

    def on_hover(self, point, hover_zone):
        if hover_zone == sublime.HOVER_TEXT:
            self.view.show_popup('<span>hover!</span>', sublime.HIDE_ON_MOUSE_MOVE_AWAY, point)
