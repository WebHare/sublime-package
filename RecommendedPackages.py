"""
Check and install WebHare recommended packages
"""

import sublime
import sublime_plugin
from package_control.package_disabler import PackageDisabler
from package_control.package_installer import PackageInstallerThread
from package_control.package_manager import PackageManager
from package_control.thread_progress import ThreadProgress
from package_control.commands.existing_packages_command import ExistingPackagesCommand


class WebhareRecommendedPackageCommand(sublime_plugin.WindowCommand, ExistingPackagesCommand, PackageDisabler):

    """
    The menu item for a single package
    """


    def __init__(self, window):

        """
        Initializes the package manager and create a list of installed packages
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        ExistingPackagesCommand.__init__(self)
        self.manager = PackageManager()
        self.package_list = self.make_package_list()


    def is_enabled(self, package):
        # pylint: disable=arguments-differ

        """
        The command is enabled if the package is not yet installed
        """

        return not self.package_installed(package)


    def is_checked(self, package):
        # pylint: disable=arguments-differ

        """
        The command is checked if the package is installed
        """

        return self.package_installed(package)


    def description(self, package):
        # pylint: disable=arguments-differ

        """
        Use the package name with its version as the menu item caption
        """

        for package_info in self.package_list:
            if package_info[0] == package:
                return package_info[0] + " (" + package_info[2].split(";", 1)[0] + ")"
        return package


    def run(self, package):
        # pylint: disable=arguments-differ

        """
        Installs the package
        """

        # Check if not already installed
        if not self.package_installed(package):

            if package in self.disable_packages(package, 'install'):
                def on_complete():
                    # pylint: disable=missing-docstring
                    self.reenable_package(package, 'install')
            else:
                on_complete = None

            # Install the package in a separate thread
            thread = PackageInstallerThread(self.manager, package, on_complete)
            thread.start()
            ThreadProgress(
                thread,
                'Installing package %s' % package,
                'Package %s successfully installed' % (package)
            )


    def package_installed(self, package):

        """
        Checks if the package is installed

        ADDME: Also check if package is up-to-date?
        """

        for package_info in self.package_list:
            if package_info[0] == package:
                return True
        return False




class WebhareInstallRecommendedPackagesCommand(sublime_plugin.WindowCommand, ExistingPackagesCommand, PackageDisabler):

    """
    The command which installs all recommended packages currently not installed
    """


    def __init__(self, window):

        """
        Initializes the package manager and create a list of installed packages
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        ExistingPackagesCommand.__init__(self)
        self.manager = PackageManager()
        self.package_list = self.make_package_list()


    def run(self):

        """
        Starts the installation in a separate thread
        """

        def start_install():

            """
            Installs all packages currently not installed
            """

            # Find submenu with id "webhare-recommended" (the "Recommended Packages" submenu)
            menu = self.find_menu("webhare-recommended")
            if not "children" in menu:
                return

            package = None
            for item in menu["children"]:

                # Check if it's a recommended package command
                if "command" in item and item["command"] == "webhare_recommended_package" and "args" in item:
                    package = item["args"]["package"]

                    # Check if not already installed
                    if not self.package_installed(package):

                        if package in self.disable_packages(package, 'install'):
                            def on_complete():
                                # pylint: disable=missing-docstring
                                self.reenable_package(package, 'install')
                        else:
                            on_complete = None

                        # Install the package and wait for the thread to finish
                        thread = PackageInstallerThread(self.manager, package, on_complete)
                        thread.start()
                        ThreadProgress(
                            thread,
                            'Installing package %s' % package,
                            'Package %s successfully installed' % (package)
                        )
                        thread.join()

        sublime.set_timeout_async(start_install, 10)


    def find_menu(self, menuid):

        """
        Finds the menu item with the given id
        """

        # Read the menu file
        menu = sublime.load_resource("Packages/WebHare/Main.sublime-menu")
        menu = sublime.decode_value(menu)
        return self.find_menu_recursive(menu, menuid)


    def find_menu_recursive(self, items, menuid):

        """
        Finds the menu item with the given id within the list of items, recursively
        """

        for item in items:
            if "id" in item and item["id"] == menuid:
                return item
            if "children" in item:
                found = self.find_menu_recursive(item["children"], menuid)
                if found:
                    return found
        return None


    def package_installed(self, package):

        """
        Checks if the package is installed

        ADDME: Also check if package is up-to-date?
        """

        for package_info in self.package_list:
            if package_info[0] == package:
                return True
        return False
