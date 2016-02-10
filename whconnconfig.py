import sublime
import os, re, subprocess, sys

try:
  from package_control import package_manager
except ImportError:
  pass



# Load the WebHare connection configuration and WebDav mounts
def load_whconn_config(filename):

  # Load the package settings
  settings = sublime.load_settings("WebHare.sublime-settings")

  # Get the local interface url and login
  whfsroot = settings.get("local_interface", "")
  username = settings.get("local_username", "")
  password = settings.get("local_password", "")

  # Read WebDAV mounts from settings, or from system if not explicitly set
  webdavmounts = settings.get("webdav_mounts")
  if len(webdavmounts) == 0:

    if sys.platform.startswith("darwin") or sys.platform.startswith("linux"):
      # On OSX, we'll read the output of the "mount" command
      mountpoint_parser = re.compile(r"^(http.*) on (.*) (\(webdav|type fuse )")
      mountpoints = subprocess.Popen([ "mount" ], stdout=subprocess.PIPE).communicate()[0].decode("utf-8").split("\n")
      #print(mountpoints)
      for mountpoint in mountpoints:
        result = mountpoint_parser.match(mountpoint)
        if result:
          url = result.group(1)
          path = result.group(2)
          webdavmounts.append({ "url": url, "path": path })

    elif sys.platform.startswith("win"):
      # On Windows, we'll read the output of the "net use" command
      mountpoint_parser = re.compile(r"\s+(\w:)\s+(\\\\\S+)")
      # shell=True prevents a cmd from being opened for execution of the command
      mountpoints = subprocess.Popen([ "net", "use" ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode("utf-8").split("\n")
      #print(mountpoints)
      for mountpoint in mountpoints:
        result = mountpoint_parser.match(mountpoint)
        if result:
          # Convert to proper url, e.g. "\\webhare.b-lex.com@SSL\webdav" to "https://webhare.b-lex.com/webdav"
          url = result.group(2).replace("\\", "/")
          if url.find("@SSL") > 0:
            url = "https:" + url.replace("@SSL", "")
          else:
            url = "http:" + url
          path = "/" + result.group(1) + "/"
          webdavmounts.append({ "url": url, "path": path })
    '''
    elif sys.platform.startswith("linux") and os.uname().nodename == "ubuntu":
      #ADDME: Don't try to read distribution type, but do a check on required commands being available, i.e. check if gvfs is
      #       available, or another command to mount webdav shares
      # On Ubuntu, we'll read the gvfs mounts
      # Find the directory where gvfs itself is mounted
      gvfspath = None
      mountpoint_parser = re.compile(r"^gvfsd-fuse on ([^ ]*)")
      mountpoints = subprocess.Popen([ "mount" ], stdout=subprocess.PIPE).communicate()[0].decode("utf-8").split("\n")
      for mountpoint in mountpoints:
        result = mountpoint_parser.match(mountpoint)
        if result:
          gvfspath = result.group(1)
      #print(gvfspath)

      if gvfspath:
        # The gvfs mounts are the directories within the gvfs mount directory
        mountpoint_parser = re.compile(r"^dav:host=([^,]*)(,ssl=true)?")
        mountpoints = subprocess.Popen([ "ls", gvfspath ], stdout=subprocess.PIPE).communicate()[0].decode("utf-8").split("\n")
        for mountpoint in mountpoints:
          result = mountpoint_parser.match(mountpoint)
          if result:
            url = "http" + ("s" if result.group(2) else "") + "://" + result.group(1) + "/"
            path = gvfspath + "/" + mountpoint
            webdavmounts.append({ "url": url, "path": path })
    '''

  # Use the file path of the active view for context
  contexturl = filename
  if not contexturl:
    contexturl = whfsroot
  elif sys.platform.startswith("win"):
    contexturl = "/" + contexturl.replace("\\", "/")

  # Determine WebHare package version
  try:
    manager = package_manager.PackageManager()
    metadata = manager.get_metadata("WebHare")
    version = metadata.get("version") if metadata else "unversioned"
  except:
    version = "version error"

  # Final configuration
  config = { "localinstalls": settings.get("local_installs"),
             "local_interface": settings.get("local_interface"),
             "webdavmounts": webdavmounts,
             "support_webdavlinks": False,
             "fallbackcontexturl": whfsroot,
             "version": version
           }

  return whfsroot, username, password, contexturl, config
