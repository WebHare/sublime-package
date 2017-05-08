# sublime-package
WebHare integration for Sublime Text

## To hack on this package
- Remove any installed version of the package
  - Close all edit windows first! (you will be removing syntax highlighting files and Sublime may not like that while running)
  - Command window (cmd/ctrl + shift + P)
  - Remove Package > WebHare
- Go to your `~/Library/Application Support/Sublime Text 3/Packages`
- Clone the repo, eiter of:
  - `git clone https://github.com/WebHare/sublime-package WebHare`
  - `git clone git@github.com:WebHare/sublime-package.git WebHare`

To prepare a new release, add a tag with a higher semver to a commit. Pushing
to github is enough to deploy. Do not forget to push the tag too!

## Debugging tips
Remember ctrl+backquote opens the Console to see errors

## Background info
- [Completions](http://docs.sublimetext.info/en/latest/reference/completions.html)
- [Snippets](http://docs.sublimetext.info/en/latest/extensibility/snippets.html)
