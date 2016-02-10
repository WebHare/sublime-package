import os, re, shlex, subprocess, sys

# Cached command to run on Linux
reveal_command = None


def reveal_file(filename):

  if sys.platform.startswith("darwin"):
    # Mac OS X: Use AppleScript to tell the Finder to reveal the file and activate
    script = 'tell application "Finder" to reveal POSIX file "' + filename + '"\ntell application "Finder" to activate'
    command = [ "/usr/bin/osascript", "-e", script ]
    subprocess.Popen(command)

  elif sys.platform.startswith("win"):
    # Windows: Start Explorer with the file selected
    command = 'explorer.exe /select,"' + filename + '"'
    subprocess.Popen(command)

  elif sys.platform.startswith("linux"):
    # Linux: We'll have to lookup the default handler for directories
    global reveal_command
    find_file_handler()
    if reveal_command:
      # Run the handler command with the file path as argument
      command = list(reveal_command)
      command.append(filename)
      subprocess.Popen(command)


def find_file_handler(self):

  global reveal_command
  if not reveal_command:
    try:
      #ADDME: Support for system without support for xdg-mime?
      # Run xdg-mime to retrieve the handler (.desktop file) for directories
      command = [ "xdg-mime", "query", "default", "inode/directory" ]
      proc = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE)
      data = proc.communicate()
      desktop = data[0].decode("utf-8").strip()

      # Find the .desktop file, look in some standard locations
      # First, check if the user has this file defined
      desktop_path = os.path.expanduser("~/.local/share/applications/" + desktop)
      if not os.path.exists(desktop_path):
        # Check for a KDE-specific file
        desktop_path = "/usr/share/applications/kde4/" + desktop
      if not os.path.exists(desktop_path):
        # Check for a global file
        desktop_path = "/usr/share/applications/" + desktop
      # Do we have an existing file now?
      if not os.path.exists(desktop_path):
        raise Exception

      # Read the file contents
      desktop_file = open(desktop_path, "r")
      desktop_text = desktop_file.read()
      desktop_file.close()
      # Look for the line starting with "Exec=", which contains the command to run
      matches = re.findall(r"Exec\=(.+)", desktop_text)
      if not matches:
        raise Exception

      handler = shlex.split(matches[0])[0]
      # For dolphin, specifiy the select argument to select the file instead of opening it
      if handler == "dolphin":
        reveal_command = [ handler, "--select" ]
      else:
        reveal_command = [ handler ]

    except Exception as e:
      sys.stderr.write("Unable to determine file manager" + str(e) + "\n")
