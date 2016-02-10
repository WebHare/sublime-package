import sublime
import styled_popup



# If StyledPopup is available, use it, otherwise use the default popup
def show_popup(content, *args, **kwargs):
  win = sublime.active_window()
  if win:
    show_view_popup(win.active_view(), content, *args, **kwargs)

def show_view_popup(view, content, *args, **kwargs):
  if view == None:
    return

  try:
    styled_popup.show_popup(view, content, *args, **kwargs)
  except:
    view.show_popup(content, *args, **kwargs)
