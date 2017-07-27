import sublime, sublime_plugin
import copy, json, os, re, socket, subprocess, sys, webbrowser
from threading import Timer
from SublimeLinter.lint import highlight
from xmlrpc.client import ServerProxy, Error
from urllib.parse import urlsplit, urlunsplit, quote_plus
from .WebSocketSupport import run_websocket_command
from .findbuffer import FindBuffer
from .whconnconfig import load_whconn_config
from .popups import show_popup

# The last retrieved file list
filelist = []
lastfilepanel = None

validate_result_dict = {}
lintdatagetter = None


def storeLinterDataGetter(getter):
  lintdatagetter = getter

def getViewStoredData(view, force=False):
  global validate_result_dict

  if not validate_result_dict:
    validate_result_dict = {}

  if view.id() not in validate_result_dict:
    if not force:
      return None
    validate_result_dict[view.id()] = {}

  return validate_result_dict[view.id()]


# The command to call to get and show a new stack trace
class GetStacktraceCommand(sublime_plugin.WindowCommand):

  def run(self):

    global filelist

    # Get the error list and save the stacktrace
    sublime.status_message("Retrieving stacktrace")
    caller = EditorSupportCall(self.window.active_view())
    result = caller.call("getremoteerrorlist")

    if not result:
      # Clear the stacktrace
      filelist = []
    else:
      print(result)
      if not "stack" in result:
        # Clear the stacktrace and display a message
        filelist = []
        sublime.status_message("No stacktrace received")
        return

      # If we have a stacktrace, show it, otherwise display a message
      filelist = result["stack"]
      if len(filelist) > 0:
        self.window.run_command("show_stacktrace")
      else:
        sublime.message_dialog("No stacktrace to show")



# The command to call to show the last stack trace (get a new one if there is none retrieved yet)
class ShowStacktraceCommand(sublime_plugin.WindowCommand):

  def run(self):

    global filelist

    # If there is no stacktrace available, get a new stacktrace, otherwise show the stacktrace
    if len(filelist) == 0:
      self.window.run_command("get_stacktrace")
    else:
      panel = FileListPanel(self.window)
      panel.show(filelist)



# The command to call to search a symbol and show the results
class SymbolSearchCommand(sublime_plugin.WindowCommand):

  # FindBuffer object
  findbuffer = FindBuffer()


  def run(self, query = False):

    view = self.window.active_view()

    # Get the selected word
    region = view.sel()[0]
    region = view.word(region.a)
    word = view.substr(region).strip()

    if query:
      # If no text is selected, use the previous query as initial query text
      if not word:
        word = self.findbuffer.get()

      # Ask for search string
      panel = self.window.show_input_panel("Symbol Search:", word, self.on_done, None, None)

      # Select the input text
      sel = panel.sel()
      sel.clear()
      sel.add(sublime.Region(0, panel.size()))
    else:
      # Use the selected word
      self.on_done(word)


  def on_done(self, word):

    #print("'"+word+"'")
    if not word:
      sublime.status_message("Nothing to search for")
      return

    # Store the query text for the next search call
    self.findbuffer.set(word)

    # Get the error list and save the stacktrace
    sublime.status_message("Searching")
    caller = EditorSupportCall(self.window.active_view())
    if word.endswith('*'):
      result = caller.call("symbolsearch", word[:-1]) # strip last char (the *)
      autoopen = False
    else:
      result = caller.call("symbolsearch", "\"" + word + "\"")
      autoopen = True

    if result:
      print(result)
      if not "results" in result:
        # Display a message
        sublime.status_message("No results received")
        return

      sublime.status_message("")

      # If we have results, show them, otherwise display a message
      resultlist = result["results"]
      if len(resultlist) > 0:
        panel = FileListPanel(self.window)
        panel.show(resultlist, autoopen)
      else:
        if not autoopen:
          panel = self.window.show_input_panel("Symbol Search:", word, self.on_done, None, None)

        sublime.message_dialog("No results to show for '" + word + "'")

class MouseSymbolSearch(sublime_plugin.TextCommand):

  def run_(self, edit, args):

    # Run the command set in the args to select the word
    system_command = args["command"] if "command" in args else None
    if system_command:
      system_args = dict({ "event": args["event"] }.items())
      if "args" in args:
        system_args.update(dict(args["args"].items()))
      self.view.run_command(system_command, system_args)

    # Get the selected word
    region = self.view.sel()[0]
    line = self.view.substr(self.view.line(region.a))
    region = self.view.word(region.a)
    word = self.view.substr(region).strip()

    caller = EditorSupportCall(self.view)

    isloadlib = re.search(r'loadlib[\s\n]*"([^"]*)"', line, re.I);
    result = None
    if isloadlib:
      result = caller.call("resolveuri", isloadlib.group(1))
    else:
      result = caller.call("symbolsearch", "\"" + word + "\"")

    if result:
      print(result)
      if not "results" in result:
        return

      # If we have results, show them, otherwise display a message
      resultlist = result["results"]
      if len(resultlist) > 0:
        panel = FileListPanel(self.view.window())
        panel.show(resultlist, False)


# The command to call to search a symbol and show the documentation in a browser
class DocumentationSearchCommand(sublime_plugin.WindowCommand):

  # FindBuffer object
  findbuffer = FindBuffer()


  def run(self, query = False):

    view = self.window.active_view()

    # Get the selected word
    region = view.sel()[0]
    region = view.word(region.a)
    word = view.substr(region).strip()

    if query:
      # If no text is selected, use the previous query as initial query text
      if not word:
        word = self.findbuffer.get()

      # Ask for search string
      panel = self.window.show_input_panel("Documentation Search:", word, self.on_done, None, None)

      # Select the input text
      sel = panel.sel()
      sel.clear()
      sel.add(sublime.Region(0, panel.size()))
    else:
      # Use the selected word
      self.on_done(word)


  def on_done(self, word):

    #print("'"+word+"'")
    if not word:
      sublime.status_message("Nothing to search for")
      return

    # Store the query text for the next search call
    self.findbuffer.set(word)

    # Get the error list and save the stacktrace
    sublime.status_message("Searching")
    caller = EditorSupportCall(self.window.active_view())
    result = caller.call("documentationsearch", "\"" + word + "\"")

    if result:
      print(result)
      if not "url" in result:
        # Display a message
        sublime.status_message("No results received")
        return

      # If we have a url, open it, otherwise display a message
      if result["url"]:
        # Read preferences
        prefs = sublime.load_settings("WebHare.sublime-settings")
        docbrowser = prefs.get("documentation_browser", "")
        if not docbrowser:
          docbrowser = None
        controller = webbrowser.get(docbrowser)
        if controller:
          controller.open_new(result["url"])
          sublime.status_message("")
        else:
          sublime.status_message("Unknown browser '" + docbrowser + "'")
      else:
        sublime.status_message("No results to show for '" + word + "'")



# The command to call to search a symbol and show the documentation in a popup
class DocumentationPopupCommand(sublime_plugin.WindowCommand):

  def run(self, query = False):

    view = self.window.active_view()

    # Get the selected word
    region = view.sel()[0]
    region = view.word(region.a)
    word = view.substr(region).strip()

    # Request documentation popup content
    caller = EditorSupportCall(self.view)
    result = caller.call("symbolsearch", "\"" + word + "\"")
    if result["results"]:
      content = ""
      for res in result["results"]:
        if content != "":
          content += "<br>"
        if "commenttext" in res and res["commenttext"] != "":
          content += res["commenttext"].replace("\n", "<br>") + """<br>"""
        content += """<span class="storage type">""" + res["definition"].replace(" ", """&nbsp;""") + """<br></span>"""
      #content = """
      #  <span class="comment block documentation">/** Format a DATETIME value */</span><br><span class="storage modifier">PUBLIC</span>
      #  <span class="storage type">STRING FUNCTION</span>
      #  <span class="name">FormatDateTime</span>(<span class="storage type">DATETIME</span>
      #  <span class="name">value</span>)
      #  """
      show_popup(content, max_width=800)

# The command to call to search a symbol and show the documentation in a popup
class MouseDocumentationPopupCommand(sublime_plugin.TextCommand):

  def run_(self, edit, args):

    # Run the command set in the args to select the word
    system_command = args["command"] if "command" in args else None
    if system_command:
      system_args = dict({ "event": args["event"] }.items())
      if "args" in args:
        system_args.update(dict(args["args"].items()))
      self.view.run_command(system_command, system_args)

    # Get the selected word
    region = self.view.sel()[0]
    region = self.view.word(region.a)
    word = self.view.substr(region).strip()

    caller = EditorSupportCall(self.view)
    result = caller.call("symbolsearch", "\"" + word + "\"")
    if result and result["results"]:
      content = ""
      for res in result["results"]:
        if content != "":
          content += "<br>"
        if "commenttext" in res and res["commenttext"] != "":
          content += res["commenttext"].replace("\n", "<br>") + """<br>"""
        content += """<span class="storage type">""" + res["definition"].replace(" ", """&nbsp;""") + """<br></span>"""
      #content = """
      #  <span class="comment block documentation">/** Format a DATETIME value */</span><br><span class="storage modifier">PUBLIC</span>
      #  <span class="storage type">STRING FUNCTION</span>
      #  <span class="name">FormatDateTime</span>(<span class="storage type">DATETIME</span>
      #  <span class="name">value</span>)
      #  """
      show_popup(content, max_width=800)


# The command to call to build the current file
class HarescriptBuildCommand(sublime_plugin.WindowCommand):

  def run(self, cmd = None):

    if not cmd or len(cmd) == 0:
      return
    cmd = cmd[0]

    # Get the error list and save the stacktrace
    sublime.status_message("Building")
    caller = EditorSupportCall(self.window.active_view())
    result = caller.call(cmd)

    if result:
      print(result)
      if not "errors" in result and not "warnings" in result:
        # Display a message
        sublime.status_message("No results received for " + cmd)
        return

      # If we have errors and/or warnings, show them, otherwise display a message
      results = []
      if "errors" in result:
        results = results + result["errors"]
      if "warnings" in result:
        results = results + result["warnings"]
      if len(results) > 0:
        # Prepend the message with either "Error: " or "Warning: "
        for idx, obj in enumerate(results):
          results[idx]["message"] = ("Error: " if obj["iserror"] else "Warning: ") + obj["message"]
        sublime.status_message("")
        panel = FileListPanel(self.window)
        panel.show(results)
      else:
        sublime.status_message("Built successfully without errors or warnings")



class EditorSupportCall:

  contexturl = ""
  config = {}
  browser = None


  def __init__(self, view):
    if not view:
      print("view not set")
    if not view.file_name:
      print("view no filename set")
    if not load_whconn_config:
      print("no load_whconn_config")

    havefileconfig, fileconfig = self.getfileconfig(view.file_name())
    if havefileconfig:
      whfsroot, username, password, contexturl, config = fileconfig
    else:
      # Load the connection settings, use the file path of the active view for context
      whfsroot, username, password, contexturl, config = load_whconn_config(view.file_name())

    self.contexturl = contexturl
    self.config = config

    # Construct the RPC url and setup a server proxy for the RPC calls
    up = urlsplit(whfsroot)
    self.adminurl = urlunsplit((up.scheme, quote_plus(username) + ":" + quote_plus(password) + "@" + up.netloc, "/wh_services/blex_alpha/editorsupport", "", ""))
    self.browser = ServerProxy(self.adminurl)

  def getfileconfig(self, filename):
    curr = filename
    maxdepth = 20

    if not curr:
      return False, None

    while --maxdepth > 0 and curr != "/":
      curr = os.path.normpath(os.path.join(curr, ".."))
      testfile = os.path.join(curr, ".wh.connectinfo")
      res, tryfile, config = self.readfileconfig(filename, testfile)
      if res:
        if tryfile:
          res2, tryfile2, config2 = self.readfileconfig(filename, tryfile)
          if res2:
            return True, config2
        return True, config
    return False, None

  def readfileconfig(self, filename, testfile):
    if os.path.isfile(testfile):
      with open(testfile) as data_file:
        print("found config file at", testfile)
        data = json.load(data_file)

        tryfile = data["tryfile"] if "tryfile" in data else ""
        whfsroot = data["url"]
        username = data["user"]
        password = data["password"]
        contexturl = filename
        port = urlsplit(whfsroot).port
        config = { "local_interface": whfsroot
                 , "localinstalls":
                    [ { "name": "local"
                      , "peertitle": ""
                      , "paths": [ os.path.normpath(os.path.join(testfile, "..")) ]
                      , "ports": [ port ]
                      , "interface": whfsroot
                      }
                    ]
                 }
        return True, tryfile, ( whfsroot, username, password, contexturl, config )
    return False, None, None

  def call(self, method, param1 = None, param2 = None):

    try:
      # Set (global) socket timeout globally
      socket.setdefaulttimeout(10)

      # Call the remote function and return the result
      if method == "getremoteerrorlist":
        return self.browser.getRemoteErrorList(self.contexturl, self.config)
      elif method == "symbolsearch":
        return self.browser.symbolSearch(param1, self.contexturl, self.config)
      elif method == "documentationsearch":
        return self.browser.documentationSearch(param1, self.contexturl, self.config)
      elif method == "validate":
        return self.browser.validate(self.contexturl, self.config)
      elif method == "compile":
        self.config["force"] = True
        return self.browser.compile(self.contexturl, self.config)
      elif method == "validateharescriptsource":
        return self.browser.validateharescriptsource(self.contexturl, param1, self.config)
      elif method == "getloadlibsuggestions":
        return self.browser.rpc_getloadlibsuggestions(self.contexturl, param1, self.config)
      elif method == "addloadlibtosource":
        return self.browser.rpc_addloadlibtosource(self.contexturl, param1, param2, self.config)
      elif method == "resolveuri":
        return self.browser.rpc_resolveuri(self.contexturl, param1, self.config)

    except Error as e:
      # Display a message
      sublime.status_message("Error retrieving " + method + " result")
      print("Error", e)
      return None

    except IOError as e:
      # Display a message
      sublime.status_message("Error connecting to server")
      print("IOError", e, self.adminurl)
      return None

    except socket.error as e:
      # Display a message
      sublime.status_message("Error connecting to server")
      print("socket.error", e, self.adminurl)
      return None

    finally:
      # Reset (global) socket timeout to default value
      socket.setdefaulttimeout(None)

    #ADDME: Fallback to running local 'wh' call?


class FileListPanel:

  entries = []
  window = None
  orgview = None
  orgsel = []
  orgpos = None
  onselect = None
  openedfile = False


  def __init__(self, window):

    self.window = window

    global lastfilepanel

    # if we're replacing another filelistpanel, copy its original location
    if lastfilepanel != None:
      self.orgview = lastfilepanel.orgview
      self.orgsel = lastfilepanel.orgsel
      self.orgpos = lastfilepanel.orgpos
    else:
      # Store a reference to the currently active view with its current selection and viewport, so we can restore it if no file
      # was actually opened
      self.orgview = self.window.active_view()
      if self.orgview:
        self.orgsel = []
        for region in self.orgview.sel():
          self.orgsel.append(region)
        self.orgpos = self.orgview.viewport_position()

    # Now, this object is the current shown filelistpanel
    lastfilepanel = self


  def show(self, entries, autoopen = False, onselect = None):

    self.entries = entries
    self.onselect = onselect

    # Create the list of files in the stacktrace
    items = []
    # Keep the index of the first external library
    firstexternal = -1
    for entry in self.entries:
      # Show multiple lines per item, first the message or function, then the file path
      lines = []

      # The first entry has an error message, subsequent entries have function names (truncate at 100 characters)
      if "message" in entry:
        lines.append((entry["message"][:97] + '...') if len(entry["message"]) > 100 else entry["message"])
      elif "function" in entry:
        lines.append(entry["function"])
      elif "func" in entry: #ADDME: Why function/func difference?
        lines.append(entry["func"])
      elif "name" in entry:
        lines.append(entry["name"])
      else:
        lines.append("")

      editorpath = entry["editorpath"]
      if sys.platform.startswith("win"):
        if (editorpath != "" and editorpath != "(hidden)"):
          editorpath = editorpath[1:].replace("/", "\\")
          print("parsed",editorpath)
          self.entries[len(items)]["editorpath"] = editorpath
      lines.append(editorpath + ":" + str(entry["line"]) + ":" + str(entry["col"]))

      # Check if this is the first external library
      if "filename" in entry:
        if (firstexternal < 0 and
            not (entry["filename"] == "(hidden)"
              or entry["filename"] == ""
              or entry["filename"].startswith("wh::")
              or entry["filename"].startswith("mod::consilio/")
              or entry["filename"].startswith("mod::system/")
              or entry["filename"].startswith("mod::publisher/")
              or entry["filename"].startswith("mod::tollium/")
              or entry["filename"].startswith("mod::wrd/")
              # Note: module:: and modulescript:: are obsolete now
              or entry["filename"].startswith("module::consilio/")
              or entry["filename"].startswith("module::system/")
              or entry["filename"].startswith("module::publisher/")
              or entry["filename"].startswith("module::tollium/")
              or entry["filename"].startswith("module::wrd/")
              or entry["filename"].startswith("modulescript::consilio/")
              or entry["filename"].startswith("modulescript::system/")
              or entry["filename"].startswith("modulescript::publisher/")
              or entry["filename"].startswith("modulescript::tollium/")
              or entry["filename"].startswith("modulescript::wrd/")
              or entry["filename"].endswith("/buildbabelexternalhelpers.js")
              or entry["filename"].endswith("/ap.js")
              or entry["filename"].endswith("/regenerator-runtime/runtime.js")
              or entry["filename"].endswith("/testframework.es")
              or entry["filename"].endswith("/testframework-rte.es")
              or entry["filename"].endswith("/testsuite.es"))):
          firstexternal = len(items)

      items.append(lines)

    if firstexternal < 0:
      firstexternal = 0

    if (autoopen and len(items) == 1):
      # There is only 1 result and it should be opened automatically
      entry = self.entries[0]

      if self.onselect != None:
        self.onselect(entry)
        return

      flags = sublime.ENCODED_POSITION
      self.window.open_file(entry["editorpath"] + ":" + str(entry["line"]) + ":" + str(entry["col"]), flags)

    else:
      # Show the list, preview file on highlight, open file on select
      self.window.show_quick_panel(items, self.on_select, 0, firstexternal, self.on_highlighted)


  def on_highlighted(self, i):

    self.openFile(i, True)
    if i >= 0:
      entry = self.entries[i]
      if "message" in entry:
        sublime.status_message(entry["message"])


  def on_select(self, i):

    self.openFile(i, False)


  def openFile(self, i, preview):

    global lastfilepanel

    if i >= 0:
      entry = self.entries[i]
      if (entry["editorpath"] != "" and entry["editorpath"] != "(hidden)"):
        if not preview and self.onselect != None:
          self.onselect(entry)
        else:
          # Open the selected file
          flags = sublime.ENCODED_POSITION | (sublime.TRANSIENT if preview else 0)
          print("open",entry["editorpath"])
          self.window.open_file(entry["editorpath"] + ":" + str(entry["line"]) + ":" + str(entry["col"]), flags)
          if not preview:
            self.openedfile = True
            if lastfilepanel == self:
              lastfilepanel = None
          return
    else:
      # If another file panel was opened already, forego restoring the original selection
      if lastfilepanel != self:
        return
      lastfilepanel = None


    # No file selected or file cannot be opened (e.g. "(hidden)"): restore focus to the originally active view (this will
    # close a currently opened preview file) and restore selection and viewport
    if self.orgview and not self.openedfile:
      sel = self.orgview.sel()
      sel.clear()
      for region in self.orgsel:
        sel.add(region)
      self.orgview.set_viewport_position(self.orgpos, False)
      self.window.focus_view(self.orgview)

# Separate class to for validation, so it can be used from the online validation listener too
class ValidateHarescript:
  view = None

  def is_enabled(self, view):
    self.view = view
    view_settings = self.view.settings()
    if re.search(r'HareScript', view_settings.get("syntax"), re.I):
      return True
    if re.search(r'XML', view_settings.get("syntax"), re.I):
      return True
    if re.search(r'Witty', view_settings.get("syntax"), re.I):
      return True

    return False

  def run(self, view):

    self.view = view

    if not self.is_enabled(view):
      return

    data = getViewStoredData(self.view, True)
    data["authorative"] = True
    buffer_text = self.view.substr(sublime.Region(0, self.view.size()))

    caller = EditorSupportCall(self.view)
    result = caller.call("validateharescriptsource", buffer_text)

    if result:
      if not "errors" in result and not "warnings" in result:
        # Display a message
        sublime.status_message("No validation results received")
        return

      if "supported" in result and not result["supported"]:
        sublime.status_message("Target server does not support validation")
        data["supported"] = False
        return

      # Manual validation worked, so automatic validation may proceed again
      data["supported"] = True

      # If we have errors and/or warnings, show them, otherwise display a message
      results = []
      if "errors" in result:
        results = results + result["errors"]
      if "warnings" in result:
        results = results + result["warnings"]
      if len(results) > 0:
        # Prepend the message with either "Error: " or "Warning: "
        for idx, obj in enumerate(results):
          results[idx]["message"] = ("Error: " if "iserror" in obj and obj["iserror"] else "Warning: " if "iserror" in obj else "") + obj["message"]
        sublime.status_message("")
        panel = FileListPanel(self.view.window())
        panel.show(results)
      else:
        sublime.status_message("Validated successfully")

    else:
      # Return error, don't repeat
      data["supported"] = False


# The command to call to manually validate
class ValidateFileCommand(sublime_plugin.TextCommand):

  def is_visible(self):
    cmd = ValidateHarescript()
    return cmd.is_enabled(self.view)

  def is_enabled(self):
    return True

  def run(self, edit):
    cmd = ValidateHarescript()
    cmd.run(self.view)


# Erase linter gutter marks when validating, they'll be re-added when validation results are received
class EraseLinterGutterMarks(sublime_plugin.EventListener):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # Load the package settings
    settings = sublime.load_settings("WebHare.sublime-settings")
    self.hidelinter = settings.get("hide_linter_while_typing", False)
    if self.hidelinter:
      print("Hiding SublimeLinter while typing")

  def on_modified(self, view):
    if self.hidelinter:
      for error_type in (highlight.WARNING, highlight.ERROR):
        view.erase_regions(highlight.GUTTER_MARK_KEY_FORMAT.format(error_type))

#  9 variable
# 76 objecttype
# 85 variable (dym)
# 88 function (dym)
#139 function
#178 objecttype (dym)
unknownsymbolerrorcodes = [ 9, 76, 85, 88, 139, 178 ]

class AddLoadlibCommand(sublime_plugin.TextCommand):
  def is_visible(self, event = None):
    # Only work on Harescript files
    view_settings = self.view.settings()
    if not re.search(r'HareScript', view_settings.get("syntax"), re.I):
      return False
    # Need validation data
    data = getViewStoredData(self.view)
    if not data or not "messages" in data:
      return False

    # Use caret position, or mouse click position if this is a click
    pos = self.view.sel()[0].a
    if event != None:
      pos = self.view.window_to_text((event["x"], event["y"]));

    # Get the current line, assert that there is an error
    firstline = self.view.rowcol(pos)[0] + 1
    for idx, obj in enumerate(data["messages"]):
      if (obj["code"] in unknownsymbolerrorcodes) and obj["line"] == firstline:
        return True
    return False
  def is_enabled(self):
    return True
  def want_event(self):
    return True

  def run(self, edit, event):
    print("event", edit, event)
    # Get validation data
    data = getViewStoredData(self.view)
    if not data or not "messages" in data:
      return

    # Use caret position, or mouse click position if this is a click
    pos = self.view.sel()[0].a
    if event != None:
      pos = self.view.window_to_text((event["x"], event["y"]));
    firstline = self.view.rowcol(pos)[0] + 1

    # Get the symbol that is missing
    word = ""
    for idx, obj in enumerate(data["messages"]):
      if (obj["code"] in unknownsymbolerrorcodes) and obj["line"] == firstline:
        word = obj["msg1"]
        break

    # Get the loadlibs this symbol is exported from
    caller = EditorSupportCall(self.view)
    result = caller.call("getloadlibsuggestions", word)

    if result:
      print(result)
      if not "results" in result:
        return

      # If we have results, show them, otherwise display a message
      resultlist = result["results"]
      print("results", resultlist)
      if len(resultlist) == 1:
        self.gotselect(resultlist[0])
      elif len(resultlist) > 1:
        panel = FileListPanel(self.view.window())
        self.edit = edit
        panel.show(resultlist, False, onselect = self.gotselect)

  def gotselect(self, entry):
    self.view.run_command("add_loadlib_text", { "path": entry["path"] })


class AddLoadlibTextCommand(sublime_plugin.TextCommand):
  def run(self, edit, path):
    print("run AddLoadlibTextCommand", path)

    buffer_text = self.view.substr(sublime.Region(0, self.view.size()))

    caller = EditorSupportCall(self.view)
    result = caller.call("addloadlibtosource", buffer_text, path)
    print("result", result)
    if not result:
      sublime.status_message("Error connecting to server")
    elif not result["success"]:
      sublime.status_message("Could not add loadlib to source, the top of the file might be messy")
    else:
      self.view.insert(edit, result["insertpos"], result["data"])
      sublime.status_message(result["message"])


def plugin_loaded():

  # Set WEBHARE_INEDITOR environment variable
  os.environ["WEBHARE_INEDITOR"] = "1"

def plugin_unloaded():

  # Unset WEBHARE_INEDITOR environment variable
  if "WEBHARE_INEDITOR" in os.environ:
    del os.environ["WEBHARE_INEDITOR"]

