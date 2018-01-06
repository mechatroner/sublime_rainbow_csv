import sublime
import sublime_plugin

def set_color_themes():
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
#        set_color_themes()


class RainbowEventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        #FIXME otimize: this works each time we open a new buffer
        set_color_themes()

