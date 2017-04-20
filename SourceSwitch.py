import sublime, sublime_plugin
import os.path, re, sys
from .findbuffer import CopyBuffer


class SourceSwitchCommand(sublime_plugin.TextCommand):
  def run(self, edit):

    file_path = self.view.file_name()
    if not file_path:
      return

    # Screen file: */screens/*.xml
    # groups:            1   2             3      4
    result = re.search(r"(.*)(\/|\\)screens(\/|\\)(.*)\.xml$", file_path)
    if result:
      library_path_lib = result.group(1) + result.group(2) + "lib" + result.group(2) + "screens"  + result.group(2) + result.group(4) + ".whlib"
      library_path_include = result.group(1) + result.group(2) + "include" + result.group(2) + "screens"  + result.group(2) + result.group(4) + ".whlib"

      # ADDME when the majority of modules switches to /lib/, swap the default around
      if os.path.isfile(library_path_lib):
        self.view.window().open_file(library_path_lib)
      else:
        self.view.window().open_file(library_path_include)

      return

    # Library file: */include/screens/*.whlib
    # groups:            1   2      3             4            5      6
    result = re.search(r"(.*)(\/|\\)(include|lib)(\/|\\)screens(\/|\\)(.*)\.whlib$", file_path)
    if result:
      screen_path = result.group(1) + result.group(2) + "screens" + result.group(2) + result.group(6) + ".xml"
      self.view.window().open_file(screen_path)
      return

    # webdesign page xml, */webdesigns/*/pages/*.xml
    result = re.search(r"(.*(\/|\\)webdesigns(\/|\\).*(\/|\\)pages(\/|\\).*)\.xml$", file_path)
    if result:
      library_path = result.group(1) + ".whlib"
      if os.path.isfile(library_path):
        self.view.window().open_file(library_path)
      return

    # webdesign page whlib, */webdesigns/*/pages/*.whlib
    result = re.search(r"(.*(\/|\\)webdesigns(\/|\\).*(\/|\\)pages(\/|\\).*)\.whlib$", file_path)
    if result:
      screen_path = result.group(1) + ".xml"
      if os.path.isfile(screen_path):
        self.view.window().open_file(screen_path)
      return

    # webdesign page xml, */tolliumapps/*.xml
    result = re.search(r"(.*(\/|\\)tolliumapps(\/|\\).*)\.xml$", file_path)
    if result:
      library_path = result.group(1) + ".whlib"
      if os.path.isfile(library_path):
        self.view.window().open_file(library_path)
      return

    # webdesign page whlib, */tolliumapps/*.whlib
    result = re.search(r"(.*(\/|\\)tolliumapps(\/|\\).*)\.whlib$", file_path)
    if result:
      screen_path = result.group(1) + ".xml"
      if os.path.isfile(screen_path):
        self.view.window().open_file(screen_path)
      return


    # C/C++ source file: *.c, *.cpp
    # groups:            1     2
    result = re.search(r"(.*)\.(c|cpp)$", file_path)
    if result:
      header_path = result.group(1) + ".h"
      self.view.window().open_file(header_path)
      return

    # C/C++ header file: *.h
    # groups:            1
    result = re.search(r"(.*)\.h$", file_path)
    if result:
      cppsource_path = result.group(1) + ".cpp"
      csource_path = result.group(1) + ".c"
      # Open the .c file if there is not .cpp file
      if os.path.isfile(cppsource_path):
        self.view.window().open_file(cppsource_path)
      elif os.path.isfile(csource_path):
        self.view.window().open_file(csource_path)
      return

    print("Unrecognized file path", file_path)


#ADDME: Use websocket to ask webhare for the loadlib path instead of using the simple heuristics
class CopyLoadlibPathCommand(sublime_plugin.WindowCommand):

  # Library file: */<module>/include/*.whlib
  # groups:                       1      2        3              4      5
  loadlib_parser = re.compile(r".*(\/|\\)([^\/\\]*(\/|\\))include(\/|\\)(.*\.whlib)$")

  def is_visible(self):
    return CopyBuffer.general_supported

  def is_enabled(self):
    if sublime.active_window().active_view():
      file_path = sublime.active_window().active_view().file_name()
      if file_path is None:
        return False
      result = self.loadlib_parser.match(file_path)
      return result != None
    return False

  def run(self):
    file_path = sublime.active_window().active_view().file_name()
    result = self.loadlib_parser.match(file_path)
    if result:
      loadlib_path = "module::" + result.group(2) + result.group(5)
      print("Copying '" + loadlib_path + "' to clipboard")
      copybuffer = CopyBuffer()
      copybuffer.set(loadlib_path)
