import sublime, sublime_plugin
import os, re, subprocess, sys, threading
from .findbuffer import FindBuffer
from .notification import Notification


# The name (and title) of the results buffer
buffer_name = "Codegrep Results"

# Is codegrep currently running?
plugin_active = False

# Codegrep options (codegrep can only search using regex at the moment)
codegrep_regex = True
codegrep_casesensitive = False



# The command to call to start codegrep
class CodegrepCommand(sublime_plugin.WindowCommand):

  # FindBuffer object
  findbuffer = FindBuffer()


  def run(self):

    if sys.platform.startswith("win"):
      sublime.message_dialog("codegrep doesn't work yet on Windows")
      return

    # Check if we're already running
    global plugin_active
    if plugin_active:
      return

    # Read preferences
    prefs = sublime.load_settings("Preferences.sublime-settings")

    # If there is an open document, retrieve selected text as the initial query text
    query = None
    window = sublime.active_window()
    view = window.active_view()
    if view and view.sel() is not None:
      # If the 'find_selected_text' preference is set to True, check if any text is selected to use as initial query text
      # (use the first selected region when there are multiple selections up until the first newline)
      find_selected_text = prefs.get("find_selected_text", False)
      if find_selected_text:
        region = view.sel()[0]
        region = view.split_by_newlines(region)[0]
        query = view.substr(region)

    # If no text is selected, use the previous query as initial query text
    if not query:
      query = self.findbuffer.get()

    # Ask for search string
    panel = window.show_input_panel("Codegrep:", query, self.on_done, None, None)

    # Select the input text
    sel = panel.sel()
    sel.clear()
    sel.add(sublime.Region(0, panel.size()))


  def on_done(self, query):

    # Check if we're actually searching for something
    if query:
      global plugin_active
      if plugin_active:
        return
      plugin_active = True

      # Store the query text for the next search call
      self.findbuffer.set(query)

      # Get or create the results buffer
      buffer = self.get_buffer()

      # Read the settings
      global codegrep_regex, codegrep_casesensitive
      prefs = sublime.load_settings("WebHare.sublime-settings")
      prefix = prefs.get("codegrep_prefix", "")
      moduleprefix = prefs.get("codegrep_moduleprefix", "")
      stdmoduleprefix = prefs.get("codegrep_stdmoduleprefix", "")
      codegrep_regex = prefs.get("codegrep_regex", True)
      codegrep_casesensitive = prefs.get("codegrep_casesensitive", False)
      codegrep_context = prefs.get("codegrep_context", 0)
      # Read preferences
      prefs = sublime.load_settings("Preferences.sublime-settings")
      buildenv = prefs.get("build_env", None)

      # Run runscript with the codegrep script
      args = ["wh", "dev:codegrep"]
      if not codegrep_casesensitive:
        args.append("-i")
      if prefix:
        args.extend(["--prefix", prefix])
      if moduleprefix:
        args.extend(["--moduleprefix", moduleprefix])
      if stdmoduleprefix:
        args.extend(["--stdmoduleprefix", stdmoduleprefix])
      if codegrep_context:
        args.extend(["--context", str(codegrep_context)])
      args.extend(["--", query])

      # Create an environment
      current_env = os.environ.copy()
      if buildenv:
        current_env["PATH"] = buildenv.get("PATH", current_env["PATH"])

      # Initialize and start the thread running the actual search
      thread = CodegrepThread(query, buffer, args, current_env)
      thread.start()


  def get_buffer(self):

    # Find the Codegrep results view (we cannot use find_open_file as it searches for file names and not view names)
    window = sublime.active_window()
    buffer = view = next((view for view in window.views()
      if view.name() == buffer_name and view.file_name() is None), None)

    if buffer is not None:
      # Switch to the results window
      window.focus_view(buffer)

    else:
      # No result view found, create a new file
      buffer = window.new_file()

      # Set the buffer name, by which we can it again
      buffer.set_name(buffer_name)

      # Set some general settings
      settings = buffer.settings()
      settings.set("line_numbers", False)
      settings.set("scroll_past_end", True)
      settings.set("spell_check", False)
      settings.set("translate_tabs_to_spaces", True)
      settings.set("use_tab_stops", False)

      # Disable 'dirty' marking
      buffer.set_scratch(True)

      # Set syntax to (internal) Find Results syntax (also used for Find in Files)
      buffer.set_syntax_file("Packages/Default/Find Results.hidden-tmLanguage")

    return buffer



# The thread running the codegrep script and parsing the output
class CodegrepThread(threading.Thread):

  # Regular expression to parse codegrep output
  codegrep_parser = re.compile(r"^([^:]+):(\d+):(\d+):(.*)$")

  # Notifications object
  notification = Notification()


  def __init__(self, query, buffer, args, env):

    threading.Thread.__init__(self)

    # Store attributes
    self.query = query
    self.buffer = buffer
    self.cmd = args
    self.env = env

    # Read tabsize here, while we're still on the main thread
    self.tabsize = buffer.settings().get("tab_size")

    # Check if the user wants notifications
    prefs = sublime.load_settings("WebHare.sublime-settings")
    self.notify = prefs.get("codegrep_notify", False)


  def run(self):

    # Show header
    global codegrep_regex, codegrep_casesensitive
    header = "Codegrepping for \"" + self.query + "\""
    options = []
    if codegrep_regex:
      options.append("regex")
    if codegrep_casesensitive:
      options.append("case sensitive")
    if options:
      header += " (" + ", ".join(options) + ")"
    self.add_to_buffer({"new_codegrep": True, "line": header + "\n"})

    # Start the Codegrep process
    proc = subprocess.Popen(self.cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)

    numresults = 0
    numfiles = 0
    prevfile = None
    prevline = 0

    global plugin_active
    while plugin_active:

      # Read process output
      data = proc.stdout.readline()
      if len(data) == 0:
        data = proc.stderr.readline()
        if len(data) == 0:
          break

      # Try to parse the output line
      line = data.decode("utf-8")
      result = self.codegrep_parser.match(line)

      if result is not None:
        # We have a new result

        resultfile = result.group(1)
        resultline = result.group(2)
        resultcol = result.group(3)
        resultmatch = result.group(4).rstrip("\r")

        # It's a match if the column > 0 (otherwise it's context)
        if resultcol != "0":
          numresults = numresults + 1

        # If this result is for a new file, create a new file header
        if resultfile != prevfile:
          prevfile = resultfile
          prevline = 0
          numfiles = numfiles + 1
          self.add_to_buffer({"line": "\n" + resultfile + ":\n"})

        # If this result is on the same line as the previous result, skip it (avoid duplicate result lines)
        if resultline == prevline:
          continue
        if resultline != "0":
          prevline = resultline

        if resultline == "0":
          # This is an empty context line (...)
          self.add_to_buffer({"line": " " + ("." * len(str(prevline))).rjust(4) + "\n"})
        else:
          # Convert tabs to spaces, so query matching works properly (a tab may take up more than one character in the buffer)
          resultmatch = resultmatch.replace("\t", " " * self.tabsize)

          # Show the line number and match (if showing context, only show the ":" after matching line numbers)
          self.add_to_buffer({"line": " " + resultline.rjust(4)
                                      + (":" if resultcol != "0" else " ")
                                      + " " + resultmatch + "\n",
                              "query": self.query
                             })

      else:
        # Cannot parse this line, just display it
        self.add_to_buffer({"line": line})

    # If we're not killed, print footer, otherwise kill the process
    if plugin_active:

      # Results message: x matches across y files
      message = str(numresults) + " match" + ("es" if numresults != 1 else "") + " across " + str(numfiles) + " file" + ("s" if numfiles != 1 else "")

      # Show footer
      self.add_to_buffer({"line": "\n" + message + "\n"})

      # We're done
      plugin_active = False

      if self.notify:
        self.notification.notify(message, "Codegrep")

    else:

      proc.kill()


  def add_to_buffer(self, args):

    self.buffer.run_command("add_codegrep_result", args)



# This TextCommand is used to add text to the Codegrep results view (necessary to obtain an edit token)
class AddCodegrepResultCommand(sublime_plugin.TextCommand):

  # Flags used when drawing a match region
  region_flags = sublime.PERSISTENT | sublime.DRAW_NO_FILL

  def run(self, edit, **args):

    if "new_codegrep" in args and args["new_codegrep"] and self.view.size():
      # Add a newline, scroll to the end of the file for a new search and add another newline
      self.view.insert(edit, self.view.size(), "\n")
      self.view.set_viewport_position(self.view.text_to_layout(self.view.size()))
      self.view.insert(edit, self.view.size(), "\n")

    if "line" in args:
      linestart = self.view.size()

      # Show the supplied text
      self.view.insert(edit, self.view.size(), args["line"])

      # Highlight the found result
      if "query" in args and args["query"]:
        # We don't want to match the line number
        source_start = args["line"].find(": ") + 2
        regions = []

        # Find the query within the result line
        matches = re.finditer(args["query"], args["line"], re.I)
        for match in matches:
          if match.start() >= source_start:
            regions.append(sublime.Region(linestart + match.start(), linestart + match.end()))

        # Add the regions to the view
        self.view.add_regions("results_" + str(linestart), regions, "text", "", self.region_flags)

      # Set the selection to the start of the line if this is a new search
      if "new_codegrep" in args and args["new_codegrep"]:
        sel = self.view.sel()
        sel.clear()
        sel.add(sublime.Region(linestart, linestart))



# Listen for Codegrep result window close
class CodegrepListener(sublime_plugin.EventListener):

  def on_close(self, view):

    # If the results window is closed and Codegrep is active, deactivate it
    if view.name() == buffer_name and view.file_name() is None:
      global plugin_active
      if plugin_active:
        plugin_active = False



# Handler for mouse double click
class MouseGotoCodegrepCommand(sublime_plugin.TextCommand):

  # Regular expressions to parse the result buffer
  # The \n is explicitly excluded because sometimes the result_file_parser regex would return multiline results
  result_file_parser = re.compile(r"^([^\n:]+):$")
  result_line_parser = re.compile(r"^[ ]+(\d+):")


  def run_(self, edit, args):

    # The user double clicked, check if the double click was in our Codegrep results view
    if not self.open_result():
      # Run the default command in other views
      system_command = args["command"] if "command" in args else None
      if system_command:
        system_args = dict({"event": args["event"]}.items())
        system_args.update(dict(args["args"].items()))
        self.view.run_command(system_command, system_args)


  def open_result(self):

    if self.view.name() == buffer_name:

      # Get the line where the user double clicked
      point = self.view.sel()[0].a
      region = self.view.line(point)
      line = self.view.substr(region)

      # Check if this is a line with a line number
      result = self.result_line_parser.match(line)
      if result is not None:
        # Find all lines with a file name before the current line
        fileregions = (r for r in reversed(self.view.find_all(self.result_file_parser.pattern)) if r.begin() < point)
        # Get the contents of the first match (will be something like "/path/to/file:") and add the line number
        filewithpos = self.view.substr(next(fileregions)).strip() + result.group(1)
        self.view.window().open_file(filewithpos, sublime.ENCODED_POSITION)
        return True
      else:
        # Check if this is a line with a file name
        result = self.result_file_parser.match(line)
        if result is not None:
          self.view.window().open_file(result.group(1))
          return True

    return False
