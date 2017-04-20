import sublime, sublime_plugin
from package_control.package_manager import PackageManager
from package_control.commands.existing_packages_command import ExistingPackagesCommand

class WebhareRecommendedPackageCommand(sublime_plugin.WindowCommand, ExistingPackagesCommand):

    def __init__(self, window):
        sublime_plugin.WindowCommand.__init__(self, window)
        self.manager = PackageManager()
        self.package_list = self.make_package_list()

    def is_enabled(self, package):
        #ADDME: Maybe offer to install missing package directly?
        #packages = self.manager.list_packages()
        #return not(package in packages)
        return False

    def is_checked(self, package):
        #ADDME: Also check if package is up-to-date?
        for package_info in self.package_list:
            if package_info[0] == package:
                return True
        return False

    def description(self, package):
        #ADDME: Also check if package is up-to-date?
        for package_info in self.package_list:
            if package_info[0] == package:
                return package_info[0] + " (" + package_info[2] + ")"
        return package
