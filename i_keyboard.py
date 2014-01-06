import utils
import curses
from curses.textpad import Textbox, rectangle

import gettext
L = gettext.gettext

IndexFile = '/usr/share/syscons/keymaps/INDEX.keymaps'

Window = utils.Window
class Keyboard(Window):
    def __init__(self, Main):
        Window.__init__(self, Main)
        self.result = True
        self.kbd_pos  = -1
        self.scroll   =  0
        self.current  =  0
        self.tabcount = 2
        self.load()
        self.resize()

    def load(self):
        lines = []
        try:
            with open(IndexFile, 'r', encoding='iso8859_16') as index_file:
                for line in index_file:
                    if '.kbd:en:' in line:
                        lines.append(line)
        except OSError:
            self.entries = [('Failed to load keyboard maps', None)]
            return

        lines.sort()

        self.longest = 0
        self.entries = list(self.iterate(lines))

    def iterate(self, lines):
        cnt = 0
        for line in lines:
            entry = line.split('.kbd:en:')
            if len(entry) < 2:
                continue
            self.longest = max(self.longest, len(entry[1]))
            # turn into a tuple
            yield (entry[0], entry[1])

            if self.kbd_pos == -1:
                if entry[0] == 'us.unix':
                    self.kbd_pos = cnt
                cnt += 1

    def resize(self):
        self.height = min(self.Main.size[0] - 1, len(self.entries))
        self.width  = min(self.Main.size[1] - 1, self.longest+4)

        self.win.resize(*self.Main.size)
        self.win.mvwin(0, 0)

    @utils.redraw
    def event(self, key, name):
        maxpos = len(self.entries)-1
        if name == b'q':
            return False

        elif utils.isk_down(key, name):
            self.kbd_pos = min(self.kbd_pos+1, maxpos)

        elif utils.isk_up(key, name):
            self.kbd_pos = max(self.kbd_pos-1, 0)

        elif utils.isk_home(key, name):
            self.kbd_pos = 0

        elif utils.isk_end(key, name):
            self.kbd_pos = maxpos

        elif utils.isk_scrolldown(key, name):
            self.scroll = min(self.scroll+1, maxpos)

        elif utils.isk_scrollup(key, name):
            self.scroll = max(self.scroll-1, 0)

        elif utils.isk_pagedown(key, name):
            if self.kbd_pos != self.scroll + self.height - 5:
                self.kbd_pos = self.scroll + self.height - 5
            else:
                self.kbd_pos += self.height-5
            self.kbd_pos = min(maxpos, max(0, self.kbd_pos))

        elif utils.isk_pageup(key, name):
            if self.kbd_pos != self.scroll:
                self.kbd_pos = self.scroll
            else:
                self.kbd_pos -= self.height-3
            self.kbd_pos = min(maxpos, max(0, self.kbd_pos))

        elif utils.isk_right(key, name) or utils.isk_left(key, name):
            self.tab()

        elif utils.isk_enter(key, name):
            self.action()
            return False

        return True

    def tabbed(self):
        self.draw()

    def action(self):
        pass

    @utils.drawmethod
    def draw(self):
        Main   = self.Main
        width  = self.width
        height = self.height
        win    = self.win

        count  = len(self.entries)

        # hmm...
        #rectangle(win, 0, 0, height-1, width)
        #win.addstr(0, 3, '[Keyboard Layout Selection]')

        # borders
        height -= 2
        # list line
        button_line = height
        height -= 1
        win.hline(height,     1, curses.ACS_HLINE, width-1)
        win.addch(height,     0, curses.ACS_LTEE)
        win.addch(height, width, curses.ACS_RTEE)
        # -1 for the list line border
        height -= 1

        # scroll clamp
        if self.kbd_pos < self.scroll:
            self.scroll = self.kbd_pos
        elif self.scroll < self.kbd_pos - height + 1:
            self.scroll =  self.kbd_pos - height + 1

        # scrollability indicator
        if self.scroll > 0:
            win.addstr(0,        width - 16, utils.more_up)
        if self.scroll + height < count:
            win.addstr(height+1, width - 16, utils.more_down)

        x = 2
        y = 1
        eindex   = 0
        selected = self.kbd_pos - self.scroll
        for i in range(self.scroll, count):
            if y > height:
                break
            _, name = self.entries[i]
            win.addstr(y, x, name, utils.highlight_if(eindex == selected))
            eindex += 1
            y      += 1

        y = button_line
        win.addstr(y, x, L('[ OK ]'),   utils.highlight_if(self.current == 0))
        x += len(L('[ OK ]')) + 2
        win.addstr(y, x, L('[ Skip ]'), utils.highlight_if(self.current == 1))

        rectangle(win, 0, 0, self.height-1, width)
        win.addstr(0, 3, '[%s]' % L('Keyboard Layout Selection'))
