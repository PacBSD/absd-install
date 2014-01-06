import utils
import curses
from curses.textpad import Textbox, rectangle

import gettext
L = gettext.gettext

import i_keyboard
import i_parted

Window = utils.Window
class MainWindow(Window):
    def __init__(self, Main):
        Window.__init__(self, Main)

        self.title = L('Installer Main Menu')
        self.entries = [
            (L('Keyboard Selection'),  lambda: self.show_keymaps()),
            (L('Partition Editor'),    lambda: self.show_parted() ),
            (L('Quit without saving'), lambda: self.exit(False)   ),
            (L('Exit and Save'),       lambda: self.exit(True)    ),
        ]
        self.tabcount = len(self.entries)
        self.longest = len(self.title)+6
        for t,f in self.entries:
            self.longest = max(self.longest, len(t))

        self.resize()

    def resize(self):
        self.height = min(self.Main.size[0] - 1, len(self.entries)+2)
        self.width  = min(self.Main.size[1] - 1, self.longest+4)

        self.win.resize(*self.Main.size)
        self.win.mvwin(0, 0)

    def tabbed(self):
        self.draw()

    @utils.redraw
    def event(self, key, name):
        maxpos = len(self.entries)-1
        if name == b'q':
            return False

        elif utils.isk_down(key, name):
            self.current = min(self.current+1, maxpos)

        elif utils.isk_up(key, name):
            self.current = max(self.current-1, 0)

        elif utils.isk_home(key, name) or utils.isk_pageup(key, name):
            self.current = 0

        elif utils.isk_end(key, name)  or utils.isk_pagedown(key, name):
            self.current = maxpos

        elif utils.isk_enter(key, name):
            return self.action()

        return True

    def action(self):
        _, action = self.entries[self.current]
        r = action()
        self.Main.screen.erase()
        self.Main.screen.refresh()
        return r

    def exit(self, save):
        if save:
            self.Main.save()
        return False

    def show_keymaps(self):
        with i_keyboard.Keyboard(self.Main) as keyboard:
            if keyboard.run() is None:
                return False
        return True

    def show_parted(self):
        with i_parted.Parted(self.Main) as parted:
            if parted.run() is None:
                return False
        return True

    @utils.drawmethod
    def draw(self):
        Main   = self.Main
        width  = self.width
        height = self.height
        win    = self.win

        y = 1
        x = 2
        for i in range(self.tabcount):
            text, _ = self.entries[i]
            win.addstr(y, x, text, utils.highlight_if(i == self.current))
            y += 1

        rectangle(win, 0, 0, self.height-1, width)
        win.addstr(0, 3, '[%s]' % self.title)
