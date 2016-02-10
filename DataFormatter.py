import sublime, sublime_plugin
import sys, os, subprocess, threading



# The command to call to start the data formatter
class DataFormatterCommand(sublime_plugin.TextCommand):
  def run(self, edit):

    if sys.platform.startswith("win"):
      sublime.message_dialog("data_formatter doesn't work yet on Windows")
      return

    filepath = self.view.file_name()
    #filedir = os.path.dirname(filepath)

    # Read the settings
    prefs = sublime.load_settings("Preferences.sublime-settings")
    buildenv = prefs.get("build_env", None)

    # Run runscript with the dataformatter script
    args = [ "runscript", "modulescript::tollium_dev/tools/dataformatter.whscr", filepath ]

    # Create an environment
    current_env = os.environ.copy()
    if buildenv:
      current_env["PATH"] = buildenv.get("PATH", current_env["PATH"])

    # Initialize and start the thread running the actual search
    thread = DataFormatterThread(self.view, args, current_env)
    thread.start()



# The thread running the dataformatter script and displaying the output
class DataFormatterThread(threading.Thread):

  def __init__(self, buffer, args, env):

    threading.Thread.__init__(self)

    # Store attributes
    self.buffer = buffer
    self.cmd = args
    self.env = env


  def run(self):

    # Start the Data Formatter process
    proc = subprocess.Popen(self.cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)

    # Read process output
    data = proc.communicate()
    output = data[1].decode("utf-8") if data[1] else data[0].decode("utf-8")

    # Currently, the output is either AnyToString-formatted JSON/RECORD ARRAY with errors or XML
    output_format = None
    if output.startswith("JSON:") or output.startswith("+RECORD ARRAY"):
      output_format = "Packages/WebHare/AnyToString.tmLanguage"
    elif output.startswith("<"):
      output_format = "Packages/XML/XML.tmLanguage"

    self.set_buffer({ "text": output, "format": output_format })

  def set_buffer(self, args):

    # Sublime Text 2 compatibility: ST 2 requires API calls to be run within the main thread
    def _add():
      self.buffer.run_command("set_data_formatter_result", args)
    sublime.set_timeout(_add, 0)



# This TextCommand is used to add text to the Data Formatter results view (necessary to obtain an edit token)
class SetDataFormatterResultCommand(sublime_plugin.TextCommand):

  def run(self, edit, **args):

    # If a format is specified, set it
    if "format" in args and args["format"]:
      self.view.set_syntax_file(args["format"])

    # Replace all contents with the supplied text
    self.view.replace(edit, sublime.Region(0, self.view.size()), args["text"])
