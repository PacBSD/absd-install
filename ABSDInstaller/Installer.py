"""
Experimental ArchBSD Installation UI.
"""

from . import utils
from .MainWindow import MainWindow

import os
import atexit
import curses
import json

import gettext
L = gettext.gettext

CONFIG_FILE = '/tmp/absd-installer.json'

class InstallerException(Exception):
    """used mostly internally"""
    pass

class Installer(object):
    """Handles saving/reloading of previous settings. Runs the main menu, and
    keeps a yank buffer and some other data around used throughout the UI."""
    def __init__(self):
        self.size     = (1, 1)
        self.screen   = None

        self.yank_buf    = ''

        self.setup = {}

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as cfgfile:
                self.setup = json.load(cfgfile)
        except OSError:
            pass

        self.setup.setdefault('fstab',          {})
        self.setup.setdefault('bootcode',       {})
        self.setup.setdefault('mountpoint',     '/mnt')
        self.setup.setdefault('extra_packages', [])

    @property
    def fstab(self):
        """shortcut to access self.setup['fstab']"""
        return self.setup['fstab']

    @property
    def bootcode(self):
        """shortcut to access self.setup['bootcode']"""
        return self.setup['bootcode']

    def save(self):
        """Brings the current setup into a JSON-serializable form and stores
        the data in CONFIG_FILE."""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as cfgfile:
            json.dump(self.setup, cfgfile, sort_keys=True,
                      indent=4, separators=(',', ':'))
            cfgfile.write('\n')

    def __setup_gui(self):
        """Initialize default curses settings, and fetches the screen size."""
        curses.start_color()
        curses.savetty()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.screen.keypad(True)
        self.resize_event()

    @staticmethod
    def __end_gui():
        """Quit the ncurses GUI and execute 'stty sane' to bring the terminal
        into a sane state."""
        curses.resetty()
        curses.endwin()
        os.system('stty sane')

    def main(self):
        """Main entry point of the installer.
        Initializes curses, and deals with the KeyboardInterrupt gracefully."""

        atexit.register(self.__end_gui)
        self.screen = curses.initscr()

        try:
            self.__setup_gui()
            with MainWindow(self) as mainwin:
                mainwin.run()
            atexit.unregister(self.__end_gui)
            self.__end_gui()
            #self.save()
        except KeyboardInterrupt:
            pass
        except Exception as inst:
            atexit.unregister(self.__end_gui)
            self.__end_gui()
            # Now that the terminal can actually display text again
            # rethrow the exception
            raise inst

    def yank_add(self, text):
        """Replaces the yank buffer. Might some day keep a history..."""
        self.yank_buf = text

    def yank_get(self):
        """Retrieve the last yank buffer entry."""
        return self.yank_buf

    def resize_event(self):
        """Terminal resize hook. Updates the size and refreshes the screen."""
        self.size = self.screen.getmaxyx()
        self.screen.clear()
        self.screen.refresh()

    def get_key(self):
        """Used by all UIs to receive an key-press. Also reacts to KEY_RESIZE
        (terminal resizing) before the current Window deals with the new size.
        """
        key  = self.screen.getch()
        name = utils.translate_key(key)
        if key == 0x7f:
            key = curses.KEY_BACKSPACE
        elif key == 0x0a:
            key = curses.KEY_ENTER
        elif key == curses.KEY_RESIZE:
            self.resize_event()
        return (key, name)

    def __checked_fstab(self):
        """check the fstab entries for invalid or duplicate ones, when there's
        a problem, an InstallerException is raised, otherwise a list of tuples
        is returned sorted in a way that it can be mounted in order."""
        existing = set()
        ordered  = []
        for disk in self.fstab:
            # normalize
            target = os.path.normpath(self.fstab[disk])
            self.fstab[disk] = target

            # check for dups
            if target in existing:
                raise InstallerException(L('duplicate fstab entry: %s') %
                                         target)
            existing.add(target)

            # check for sanity and insert, in order
            self.__check_mountpoint(target)
            self.__insert_mountpoint(ordered, target, disk)

    @staticmethod
    def __insert_mountpoint(ordered, target, disk):
        """insert a mountpoint into a mount-ordered list"""
        best_index = 0
        components = 0
        for idx in range(0, len(ordered)):
            opath, _ = ordered[idx]
            count = Installer.__count_common_dirs(opath, target)
            if count > components:
                best_index = idx
                components = count
        ordered.insert(best_index, (target, disk))

    @staticmethod
    def __count_common_dirs(path1, path2):
        """count the common directories of path1 and path2"""
        dirs1 = Installer.__split_path(path1)
        dirs2 = Installer.__split_path(path2)
        both = min(len(dirs1), len(dirs2))
        for count in range(0, both):
            if dirs1[count] != dirs2[count]:
                return count-1
        return -1

    @staticmethod
    def __split_path(path):
        """split a path into its components by repeatedly calling
        os.path.split"""
        components = []
        while True:
            base, dirname = os.path.split(path)
            components.insert(0, dirname)
            if base == '' or base == '/':
                return components
            path = base

    @staticmethod
    def __check_mountpoint(path):
        """check a mountpoint's validity"""
        if len(path) < 1:
            # this is actually an internal error as setting a mountpoint
            # to an empty string should delete it from the dict
            raise InstallerException(L('invalid mountpoint (empty string)'))
        if path[0] != '/':
            raise InstallerException(L('invalid mountpoint: %s') % path)
        if path.find('/../') or path.endswith('/..'):
            raise InstallerException(L('illegal path for mountpoint: %s') %
                                     path)

    def __mount(self):
        """mount the filesystems specified by self.fstab to
        setup['mountpoint']"""
        raise InstallerException('TODO')

__all__ = ['Installer']
