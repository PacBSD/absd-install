#!/usr/bin/python3

print("Loading up installer...")

import utils
import i_parted

import os
import atexit
import curses
import json

def main():
    installer = Installer()
    installer.main()

###############################################################################

class Installer(object):
    def __init__(self):
        self.home        = os.environ['HOME']
        self.config_file = self.home + '/absd-installer.json'
        self.yank_buf    = ''

        self.fstab = []

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.fstab = data['fstab']
        except (FileNotFoundError, PermissionError) as inst:
            print(inst)

    def save(self):
        data = {
            'fstab': self.fstab
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, sort_keys=True,
                      indent=4, separators=(',', ':'))

    def yank_add(self, text):
        # we might add a cut/paste history at some point
        self.yank_buf = text
    def yank_get(self):
        return self.yank_buf

    def main(self):
        def exit_hook():
            try:
                self.end_gui()
            except:
                pass

        atexit.register(exit_hook)
        self.screen = curses.initscr()

        try:
            self.setup_gui()
            self.run()
            atexit.unregister(exit_hook)
            exit_hook()
        except KeyboardInterrupt:
            pass
        except Exception as inst:
            atexit.unregister(exit_hook)
            exit_hook()
            # Now that the terminal can actually display text again
            # rethrow the exception
            raise inst

    def setup_gui(self):
        curses.start_color()
        curses.savetty()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.screen.keypad(True)
        self.resize_event()

    def end_gui(self):
        curses.resetty()
        curses.endwin()
        os.system('stty sane')

    def resize_event(self):
        self.size = self.screen.getmaxyx()
        self.screen.refresh()

    def get_key(self):
        key  = self.screen.getch()
        name = utils.translate_key(key)
        if key == 0x7f:
            key = curses.KEY_BACKSPACE
        elif key == 0x0a:
            key = curses.KEY_ENTER
        return (key, name)

    def run(self):
        with i_parted.Parted(self) as parted:
            parted.run()

###############################################################################

if __name__ == '__main__':
    main()
