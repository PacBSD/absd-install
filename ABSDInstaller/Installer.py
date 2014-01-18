"""
Experimental ArchBSD Installation UI.
"""

from . import utils
from .MainWindow import MainWindow

import os
import atexit
import curses
import json
import subprocess

import geom

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

        self.yank_buf = ''

        self.setup    = {}
        self.data     = {}

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as cfgfile:
                self.setup = json.load(cfgfile)
        except OSError:
            pass

        self.setup.setdefault('fstab',          {})
        self.setup.setdefault('bootcode',       {})
        self.setup.setdefault('mountpoint',     '/mnt')
        self.setup.setdefault('extra_packages', [])
        self.setup.setdefault('done',           [])

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
            target = os.path.normpath(self.fstab[disk]['mount'])
            self.fstab[disk]['mount'] = target

            # check for dups
            if target in existing:
                raise InstallerException(L('duplicate fstab entry: %s') %
                                         target)
            existing.add(target)

            # check for sanity and insert, in order
            self.__check_mountpoint(target)
            self.__insert_mountpoint(ordered, target, disk)
        return ordered

    @staticmethod
    def __insert_mountpoint(ordered, target, disk):
        """insert a mountpoint into a mount-ordered list"""
        if target == '/':
            ordered.insert(0, (target, disk))
            return
        best_index = 0
        components = -1
        for idx in range(0, len(ordered)):
            opath, _ = ordered[idx]
            count, olen, tlen = Installer.__count_common_dirs(opath, target)
            if count > components:
                best_index = idx
                components = count
                if olen < tlen:
                    best_index += 1
        ordered.insert(best_index, (target, disk))

    @staticmethod
    def __count_common_dirs(path1, path2):
        """count the common directories of path1 and path2"""
        dirs1 = Installer.__split_path(path1)
        dirs2 = Installer.__split_path(path2)
        both = min(len(dirs1), len(dirs2))
        for count in range(0, both):
            if dirs1[count] != dirs2[count]:
                return count, len(dirs1), len(dirs2)
        return both, len(dirs1), len(dirs2)

    @staticmethod
    def __split_path(path):
        """split a path into its components by repeatedly calling
        os.path.split"""
        components = []
        while True:
            base, dirname = os.path.split(path)
            components.insert(0, dirname)
            if dirname == '':
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
        if path.find('/../') != -1 or path.endswith('/..'):
            raise InstallerException(L('illegal path for mountpoint: %s') %
                                     path)

    def __prepare_fstab(self):
        """mount the filesystems specified by self.fstab to
        setup['mountpoint']"""
        fstab              = self.__checked_fstab()
        self.data['fstab'] = fstab

        for path, disk in fstab:
            print("%s -> %s" % (disk, path))

    @staticmethod
    def __make_paths(root): # , fstab):
        """Create all the required directories on the target mountpoint."""
        for path in ['/var/log',
                     '/var/lib/pacman',
                     '/var/cache/pacman/pkg',
                     '/tmp']:
            os.makedirs('%s/%s' % (root, path), mode=0o755, exist_ok=True)

        # These are created while mounting
        #for path, disk in fstab:
        #    os.makedirs('%s/%s' % (root, path), mode=0o755, exist_ok=True)

    @staticmethod
    def __mount(mounts, what, where, fstype=None):
        """Mount a filesystem if not already mounted,
        after creating its path first."""
        if where in mounts:
            return
        os.makedirs(where, mode=0o755, exist_ok=True)
        if fstype is not None:
            subprocess.check_call(['mount', '-t', fstype, what, where])
        else:
            subprocess.check_call(['mount', what, where])

    @staticmethod
    def __mount_paths(root, fstab):
        """Mount (and if required create) all the future fstab entries."""
        mounts = [ where for what, where in geom.util.genmounts() ]
        Installer.__mount(mounts, 'procfs', '%s/proc' % root, fstype='procfs')
        Installer.__mount(mounts, 'devfs',  '%s/dev'  % root, fstype='devfs')

        for path, disk in fstab:
            Installer.__mount(mounts, disk, '%s/%s' % (root, path))

    def pacstrap(self):
        # can raise OSError
        """create obligatory directories, mount the fstab entries and install
        the system using pacman"""

        self.__prepare_fstab()

        root   = self.setup['mountpoint']
        fstab  = self.data['fstab']
        done   = self.setup['done']
        pacman = ['pacman', '--noconfirm', '--root', root]

        if 'mount' not in done:
            print(L('Mounting paths...'))
            self.__mount_paths(root, fstab)
            done.append('mount')

        if 'paths' not in done:
            print(L('Creating paths...'))
            self.__make_paths(root) #, fstab)
            done.append('paths')

        if 'sync' not in done:
            print(L('Syncing package database...'))
            if subprocess.call(pacman + ['-Sy']) != 0:
                raise InstallerException(L('Failed to sync database.'))
            done.append('sync')

        if 'download' not in done:
            print(L('Downloading packages...'))
            packages = [ '-Sw', 'base' ] + self.setup['extra_packages']
            if subprocess.call(pacman + packages) != 0:
                raise InstallerException(L('Failed to install packages.'))
            done.append('packages')

        if 'packages' not in done:
            print(L('Installing packages...'))
            packages = [ '-S', 'base' ] + self.setup['extra_packages']
            if subprocess.call(pacman + packages) != 0:
                raise InstallerException(L('Failed to install packages.'))
            done.append('packages')

__all__ = ['Installer']
