# Sublime/WebHare package
This package adds support for the WebHare Platform to Sublime. The package contains
the following:

- HareScript and Witty (the WebHare template language) syntax highlighting
- Syntax highlighting for WebHare-specific extensions (siteprl)
- Adds symbol lookup, validation, linting
- View stack traces after crash and allows direct access to the crashing file
- Automatically connects to the proper server to support these features when
  they're mounted over WebDav.

Some of these features require you to install some optional dependencies. If
you're missing one of the above features, check Preferences > Package Settings
 > WebHare > Recommended Packages to see if you have all the recommended packages

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
to github is enough to deploy, but make sure the tag is a simple 'major.minor.patch'
and not prefixed with st3-

## Debugging tips
Remember ctrl+backquote opens the Console to see errors

## Background info
- [Completions](http://docs.sublimetext.info/en/latest/reference/completions.html)
- [Snippets](http://docs.sublimetext.info/en/latest/extensibility/snippets.html)
