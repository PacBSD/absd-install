#!/usr/bin/python3

import part
import utils
import i_parted
from geom import geom

import os
import curses
import atexit
from curses.textpad import Textbox, rectangle

###############################################################################

Main = lambda: None

###############################################################################

def print_tables(tables):
    # now print the layout
    for t in tables:
        print('%s (%s) [%u, %u]' % (t.name, t.scheme, t.first, t.last))
        for p in t.partitions:
            print('\t %s (%s) [%u, %u]' % (p.name, p.partype, p.start, p.end))

def main():
    Main.screen = curses.initscr()
    atexit.register(gui_shutdown)
    try:
        setup_gui()
        start()
        destroy_gui()
    except KeyboardInterrupt:
        pass
    except Exception as inst:
        try:
            atexit.unregister(gui_shutdown)
            destroy_gui()
        except:
            pass
        raise inst

def setup_gui():
    curses.start_color()
    curses.savetty()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)

    Main.screen.keypad(True)

    # fstab entries...
    Main.fstab       = []

    # callbacks
    Main.resize_event  = resize_event
    Main.translate_key = translate_key
    Main.get_key       = get_key

    resize_event()

def destroy_gui():
    gui_shutdown()
    atexit.unregister(gui_shutdown)

def gui_shutdown():
    curses.resetty()
    curses.endwin()
    os.system('stty sane')

def resize_event():
    Main.size = Main.screen.getmaxyx()
    Main.screen.refresh()

def translate_key(key):
    try:
        return curses.keyname(key)
    except ValueError:
        return key

def get_key():
    key  = Main.screen.getch()
    name = translate_key(key)
    if key == 0x7f:
        key = curses.KEY_BACKSPACE
    elif key == 0x0a:
        key = curses.KEY_ENTER
    return (key, name)

def start():
    Main.screen.refresh()
    with i_parted.Parted(Main) as parted:
        parted.run()

if __name__ == '__main__':
    main()
