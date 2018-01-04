import sublime
import sublime_plugin

#class RainbowEventListener(sublime_plugin.EventListener):
#    def on_load(self, view):
#        view.run_command ("fold_by_level", { "level": 2 } )


class ExampleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        #self.view.insert(edit, 0, "Hello, World!")
        print("hello")
        preferences = sublime.load_settings("csv.sublime-settings")
        preferences.set("color_scheme", "Packages/Color Scheme - Default/Sixteen.tmTheme")
        sublime.save_settings("csv.sublime-settings")
