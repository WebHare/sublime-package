import subprocess, sys

class Notification:
  def __init__(self):
    self.supported = sys.platform.startswith("darwin")

  def notify(self, message, title="", subtitle="", sound=False):
    if self.supported:

      script = 'display notification "' + message + '"'
      if title != "" or subtitle != '':
        script = script + ' with'
      if title != "":
        script = script + ' title "' + title + '"'
      if subtitle != "":
        script = script + ' subtitle "' + subtitle + '"'
      if sound:
        script = script + ' sound name "NSUserNotificationDefaultSoundName"'

      command = [ "/usr/bin/osascript", "-e", script ]
      subprocess.Popen(command)

    else:
      print("Notifications not supported on this platform")
