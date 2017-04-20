import sublime, sublime_plugin
import threading
from package_control import text
from package_control.package_manager import PackageManager
from package_control.package_installer import PackageInstaller
from package_control.thread_progress import ThreadProgress
from package_control.commands.existing_packages_command import ExistingPackagesCommand

class WebhareRecommendedPackageCommand(sublime_plugin.WindowCommand, ExistingPackagesCommand):

    def __init__(self, window):
        sublime_plugin.WindowCommand.__init__(self, window)
        self.manager = PackageManager()
        self.package_list = self.make_package_list()

    def is_enabled(self, package):
        for package_info in self.package_list:
            if package_info[0] == package:
                return False
        return True

    def is_checked(self, package):
        #ADDME: Also check if package is up-to-date?
        for package_info in self.package_list:
            if package_info[0] == package:
                return True
        return False

    def description(self, package):
        for package_info in self.package_list:
            if package_info[0] == package:
                return package_info[0] + " (" + package_info[2].split(";", 1)[0] + ")"
        return package

    def run(self, package):
        thread = InstallRecommendedPackageThread(self.window, package)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')



class InstallRecommendedPackageThread(threading.Thread, PackageInstaller):

    def __init__(self, window, package):
        self.window = window
        self.package_to_install = package
        self.completion_type = 'installed'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['upgrade', 'downgrade', 'reinstall', 'pull', 'none'])

        def start_install():
            picked = -1
            idx = 0
            for package_info in self.package_list:
                if package_info[0] == self.package_to_install:
                    picked = idx
                    break
                idx = idx + 1
            self.on_done(picked)

        sublime.set_timeout(start_install, 10)
