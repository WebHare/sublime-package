import sublime, sublime_plugin
import json, subprocess, sys, threading
from ws4py.client.threadedclient import WebSocketClient

# Sublime Text 2 compatibility: Import from "urlparse" instead of "urllib.parse"
try:
  from urllib.parse import urlsplit, urlunsplit
except ImportError:
  from urlparse import urlsplit, urlunsplit

# Sublime Text 2 compatibility: Import from "filereveal" instead of ".filereveal"
try:
  from .filereveal import *
except ValueError:
  from filereveal import *

# Sublime Text 2 compatibility: Import from "whconnconfig" instead of ".whconnconfig"
try:
  from .whconnconfig import *
except ValueError:
  from whconnconfig import *

# Sublime Text 2 compatibility: Import from "popups" instead of ".popups"
try:
  from .popups import *
except ValueError:
  from popups import *

# Import the Pywin32 package if installed (for window activation on Windows)
try:
  import Pywin32.setup
  import win32gui, pywintypes
except ImportError:
  pass

# The thread that runs the actual web socket connection
thread = None


class ToggleWebsocketCommand(sublime_plugin.ApplicationCommand):

  def run(self):

    global thread

    # If we don't have a running thread, start one, otherwise stop the current thread (and close the web socket connection)
    start_websocket_thread() if not thread else stop_websocket_thread()


  def is_checked(self):

    # The menu item is checked if there is a connection
    return thread is not None



# If no thread is running yet, start a new thread and web socket connection
def start_websocket_thread():

  global thread

  if not thread:
    thread = WebHareClientThread()
    try:
      thread.start()
    except Exception as e:
      print("Could not open WebSocket connection", e)
      thread = None

    # Check if Pywin32 is installed
    if sys.platform.startswith("win"):
      try:
        installed = win32gui != None
      except NameError as e:
        sublime.error_message("Please install the Pywin32 package for additional functionality")



# If a thread is running, stop it and close the web socket connection
def stop_websocket_thread():

  global thread

  if thread:
    thread.stop()
    thread = None


def run_websocket_command(command, params=None):

  global thread

  if thread:
    thread.sock.run_command(command, params)
  else:
    status_message("WebSocket not connected")



class WebHareClientThread(threading.Thread):

  def __init__(self):

    threading.Thread.__init__(self)

    # Read the configuration
    whfsroot, username, password, contexturl, config = load_whconn_config(None)

    # Construct the WebSocket URL and create the socket
    urlparts = urlsplit(whfsroot)
    adminurl = urlunsplit(("wss" if urlparts.scheme == "https" else "ws", username + ":" + password + "@" + urlparts.netloc, "/tollium_todd.res/blex_alpha/editorsupport.whsock", "", ""))
    print("connecting to", adminurl)
    self.sock = WebHareClient(adminurl)

    self.sock.config = config


  def run(self):

    # Connect the socket
    status_message("Opening WebSocket")
    self.sock.connect()


  def stop(self):

    # If the socket is still connected, close the connection
    if not self.sock.client_terminated:
      status_message("Closing WebSocket")
      self.sock.close()



class WebHareClient(WebSocketClient):

  config = None
  _handle = None # Windows: handle to Sublime Text window

  def opened(self):

    status_message("WebSocket connected")

    # After the socket was connected, send our (WebDav) configuration
    print(self.config)
    data = json.dumps(self.config)
    self.send("config:" + data)


  def closed(self, code, reason=None):

    status_message("WebSocket disconnected")
    print("WebSocket closed", code, reason)
    # The connection was closed, maybe because of external circumstances, so stop the thread
    stop_websocket_thread()


  def run_command(self, command, params):
    data = json.dumps({"command": command,
                       "params": params
                      })
    self.send("command:" + data)


  def received_message(self, msg):

    print(msg)
    if msg.is_text:
      args = msg.data.decode("utf-8").split("\t")

      # Update available
      if args[0] == "updateavailable":
        if args[2] != "unversioned":
          sublime.message_dialog("A newer version of the WebHare package is available (" + args[1] + ")")
        else:
          sublime.status_message("WebHare package is unversioned, available version is " + args[1])

      # Open a file in the editor
      elif args[0] == "openfile":
        filename = self.parse_filename(args[1])
        self.open_file(filename)

      # Reveal a file in the Finder/Explorer
      elif args[0] == "revealfile":
        filename = self.parse_filename(args[1])
        print("reveal", filename)
        reveal_file(filename)

      # Show documentation popup
      elif args[0] == "documentationpopup":
        result = json.loads(args[1])
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
          show_popup(content, max_width=640)


  def parse_filename(self, filename):
    # On Windows, remove the leading slash and replace forward slashes with back slashes
    if sys.platform.startswith("win"):
      if filename != "":
        filename = filename[1:].replace("/", "\\")
    return filename


  def open_file(self, filename):
    # Sublime Text 2 compatibility: ST 2 requires API calls to be run within the main thread
    def _open():
      win = sublime.active_window()
      if win:
        print("open", filename)
        win.open_file(filename, sublime.ENCODED_POSITION)
        self.activate_sublime()
    sublime.set_timeout(_open, 0)


  def activate_sublime(self):
    # Mac OS X: Use AppleScript to tell Sublime Text to activate
    if sys.platform.startswith("darwin"):
      script = 'tell application "Sublime Text" to activate'

      # Sublime Text 2 compatibility: Tell application "Sublime Text 2"
      if sys.version_info < (3,):
        script = 'tell application "Sublime Text 2" to activate'

      print(script)
      command = ["/usr/bin/osascript", "-e", script]
      subprocess.Popen(command)

    # Windows: Use the Pywin32 package to find the "Sublime Text" window and set it as foreground window
    elif sys.platform.startswith("win"):
      # Based on: http://stackoverflow.com/a/2091530
      try:
        self._handle = None
        win32gui.EnumWindows(self._window_enum_callback, ".*Sublime Text.*")
        if self._handle:
          print("SetForegroundWindow", self._handle)
          win32gui.SetForegroundWindow(self._handle)
        else:
          print("Could not find Sublime Text window")

      except NameError as error:
        print(error)
      except pywintypes.error as error:
        if error.args[0] != 0:
          print(error.args[2])


  def _window_enum_callback(self, hwnd, wildcard):
    if not self._handle and re.match(wildcard, str(win32gui.GetWindowText(hwnd))) != None:
      self._handle = hwnd



def status_message(msg):
  # Sublime Text 2 compatibility: ST 2 requires API calls to be run within the main thread
  def _statmsg():
    sublime.status_message(msg)
  sublime.set_timeout(_statmsg, 0)


def plugin_loaded():

  # Open WebSocket on plugin load, after a timeout (otherwise Sublime Text 2 would freeze on the 'new version' message box)
  sublime.set_timeout(start_websocket_thread, 5000)


def plugin_unloaded():

  # Close WebSocket on plugin unload
  stop_websocket_thread()


# Sublime Text 2 compatibility: Register plugin unload handler, call plugin load handler
if sys.version_info < (3,):
  unload_handler = plugin_unloaded
  plugin_loaded()
