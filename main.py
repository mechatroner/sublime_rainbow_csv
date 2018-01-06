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


class RainbowEventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        settings = view.settings()
        syntax = settings.get('syntax')
        if syntax.find('csv.tmLanguage') == -1 and syntax.find('tsv.tmLanguage') == -1:
            return
        print("EventListener on_load triggered")
        ensure_color_scheme()


#class ViewRainbowEventListener(sublime_plugin.ViewEventListener):
#
#    @classmethod
#    def is_applicable(cls, settings):
#        return True
#        #syntax = settings.get('syntax')
#        #return syntax.find('csv.tmLanguage') != -1 or syntax.find('tsv.tmLanguage') != -1
#
#    def on_load(self, view):
#        print("ViewEventListener on_load triggered")
#        ensure_color_scheme()

