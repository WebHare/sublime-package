import sys, os, subprocess

# Import the Pywin32 package if installed (for clipboard functionality on Windows)
try:
  import Pywin32.setup
  import win32gui, win32con, win32clipboard
except ImportError:
  pass


class PasteBoard:
  """
  PasteBoard: A wrapper around pbcopy and pbpaste on OS X, SetClipboardData and GetClipboardData on Windows.
  On other platforms it just stores the text locally
  """

  buffer = ""
  pboard = ""

  # General and find buffer supported on OS X, general supported on Windows
  general_supported = sys.platform.startswith("darwin") or sys.platform.startswith("linux")
  try:
    general_supported = general_supported or win32clipboard != None
  except:
    pass
  find_supported = sys.platform.startswith("darwin")

  def __init__(self):
    if sys.platform.startswith("darwin") or sys.platform.startswith("linux"):
      # Set language to UTF-8
      self.env = os.environ.copy()
      self.env["LANG"] = "en_US.UTF-8"

  # Copy the given text to the find pasteboard
  def set(self, text):
    self.buffer = text

    if sys.platform.startswith("darwin"):
      proc = subprocess.Popen([ "pbcopy", "-pboard", self.pboard ], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=self.env)
      proc.communicate(input=self.buffer.encode("utf-8"))

    elif sys.platform.startswith("win"):
      if self.general_supported and self.pboard == "general":
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_TEXT, self.buffer)
        win32clipboard.CloseClipboard
    elif sys.platform.startswith("linux"):
      proc = subprocess.Popen([ "xclip", "-i", "-selection", "clipboard" ], shell=False, stdin=subprocess.PIPE, env=self.env)
      res = proc.communicate(input=self.buffer.encode("utf-8"))
      print("result", res)

  # Return the text pasted from the find pasteboard
  def get(self):
    if sys.platform.startswith("darwin"):
      proc = subprocess.Popen([ "pbpaste", "-pboard", self.pboard, "-Prefer", "txt" ], shell=False, stdout=subprocess.PIPE, env=self.env)
      self.buffer = proc.communicate()[0].decode("utf-8")

    elif sys.platform.startswith("win"):
      if self.general_supported and self.pboard == "general":
        win32clipboard.OpenClipboard()
        self.buffer = win32clipboard.GetClipboardData(win32con.CF_TEXT)
        win32clipboard.CloseClipboard
    elif sys.platform.startswith("linux"):
      proc = subprocess.Popen([ "xclip", "-o", "-selection", "clipboard" ], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=self.env)
      self.buffer = proc.communicate()[0].decode("utf-8")

    return self.buffer


class CopyBuffer(PasteBoard):
  def __init__(self):
    self.pboard = "general"
    PasteBoard.__init__(self)


class FindBuffer(PasteBoard):
  def __init__(self):
    self.pboard = "find"
    PasteBoard.__init__(self)
