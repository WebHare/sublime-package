import sublime, sublime_plugin
from .filereveal import reveal_file

# The command to call to reveal the currently opened file in the system's file manager
class RevealFileCommand(sublime_plugin.WindowCommand):

  def run(self):

    if self.window.active_view():
      reveal_file(self.window.active_view().file_name())
