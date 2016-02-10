import sublime, sublime_plugin

class ToggleBookmarkWholelineCommand(sublime_plugin.TextCommand):
   def run(self, edit):
      caretLine = self.view.line(self.view.sel()[0])
      oldBookmarks = self.view.get_regions("bookmarks")

      newBookmarks = []
      bookmarkFoundOnCaretLine = False

      for thisbookmark in oldBookmarks:
         # if thisbookmark.intersects(caretLine):
         if ( (thisbookmark.begin() >= caretLine.begin()) and (thisbookmark.begin() <= caretLine.end()) or
              (thisbookmark.end() >= caretLine.begin()) and (thisbookmark.end() <= caretLine.end()) ):
            bookmarkFoundOnCaretLine = True
         else:
            newBookmarks.append(thisbookmark)

      if not bookmarkFoundOnCaretLine:
            newBookmarks.append(self.view.sel()[0])

      sublime.active_window().active_view().add_regions("bookmarks", newBookmarks, "bookmarks", "bookmark", sublime.HIDDEN | sublime.PERSISTENT)
