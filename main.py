import sublime
import sublime_plugin

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

    def on_hover(self, point, hover_zone):
        if hover_zone == sublime.HOVER_TEXT:
            # FIXME use view.show_popup() instead
            self.view.set_status('rainbow_csv_hover', 'hovering!')
        else:
            self.view.set_status('rainbow_csv_hover', '')
        #print("hovering")

