"""
Experimental ArchBSD Installation UI.
"""

from . import utils, part
from .MainWindow import MainWindow

import os
import atexit
import curses
import json

CONFIG_FILE = '/tmp/absd-installer.json'

class Installer(object):
    """Handles saving/reloading of previous settings. Runs the main menu, and
    keeps a yank buffer and some other data around used throughout the UI."""
    def __init__(self):
        self.yank_buf    = ''

        self.fstab    = {}
        self.bootcode = {}
        self.size     = (1, 1)
        self.screen   = None

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as cfgfile:
                data = json.load(cfgfile)
                self.fstab    = data['fstab']
                self.bootcode = data['bootcode']
        except (FileNotFoundError, PermissionError) as inst:
            print(inst)
        except ValueError as inst:
            print("Error in old ~/absd-installer.json file")
            print(inst)

    def save(self):
        """Brings the current setup into a JSON-serializable form and stores
        the data in CONFIG_FILE."""
        data = {
            'fstab':    self.fstab,
            'bootcode': self.bootcode,
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as cfgfile:
            json.dump(data, cfgfile, sort_keys=True,
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

__all__ = ['Installer']
