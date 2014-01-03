import part
import utils
from geom import geom

import curses
from curses.textpad import Textbox, rectangle

class EntryType:
    Table     = 0
    Partition = 1
    Free      = 2

Window = utils.Window
class Parted(Window):
    def __init__(self, Main):
        Window.__init__(self, Main)

        self.Main       = Main
        self.tab_pos    = 0
        self.tab_scroll = 0

        self.load()
        self.resize()

    def resize(self):
        self.height = self.Main.size[0] - 1
        self.width  = self.Main.size[1] - 1
        self.win.resize(*self.Main.size)
        self.win.mvwin(0, 0)

    def iterate(self):
        """Entry generator function"""
        self.tab_longest = 0
        for t in self.tables:
            self.tab_longest = max(self.tab_longest, len(t.name))
            yield (EntryType.Table, t)
            at = t.first
            for p in t.partitions:
                if p.start > at:
                    yield (EntryType.Free, t, at, p.start - at)
                self.tab_longest = max(self.tab_longest, len(p.name))
                yield (EntryType.Partition, t, p)
                at = p.end + 1
            if at < t.last:
                yield (EntryType.Free, t, at, t.last - at)

    def load(self):
        self.win.clear()
        self.tables      = part.load()
        self.tab_entries = [i for i in self.iterate()]
        self.tab_pos     = min(self.tab_pos, len(self.tab_entries)-1)

    def event(self, key, name):
        maxpos = len(self.tab_entries)-1
        if   key == curses.KEY_DOWN or name == b'j' or name == b'^N':
            # Down
            self.tab_pos = min(self.tab_pos+1, maxpos)
            self.draw()
        elif key == curses.KEY_UP   or name == b'k' or name == b'^P':
            # Up
            self.tab_pos = max(self.tab_pos-1, 0)
            self.draw()
        elif key == curses.KEY_HOME or name == b'g':
            # Top:
            self.tab_pos = 0
            self.draw()
        elif key == curses.KEY_END  or name == b'G':
            # Bottom:
            self.tab_pos = maxpos
            self.draw()
        elif name == b'^E':
            # scroll down
            self.tab_scroll = min(self.tab_scroll+1, maxpos)
            self.draw()
        elif name == b'^Y':
            # scroll up
            self.tab_scroll = max(self.tab_scroll-1, 0)
            self.draw()
        elif key == curses.KEY_NPAGE:
            # page down
            if self.tab_pos != self.tab_scroll + self.height - 3:
                self.tab_pos = self.tab_scroll + self.height - 3
            else:
                self.tab_pos += self.height-3
            self.tab_pos = min(maxpos, max(0, self.tab_pos))
            self.draw()
        elif key == curses.KEY_PPAGE:
            # page up
            if self.tab_pos != self.tab_scroll:
                self.tab_pos = self.tab_scroll
            else:
                self.tab_pos -= self.height-3
            self.tab_pos = min(maxpos, max(0, self.tab_pos))
            self.draw()
        return True

    @staticmethod
    def entry_table(maxlen, w, _, t):
        return '%s%s    %s [%s]' % (t.name,
                                    ' ' * (maxlen - len(t.name)),
                                    t.scheme,
                                    part.bytes2str(t.size))

    @staticmethod
    def entry_partition(maxlen, w, _, t, p):
        return '  => %s%s%- 14s [%s]' % (p.name,
                                         ' ' * (maxlen - len(p.name)),
                                         p.partype,
                                         part.bytes2str(p.bytes_))

    @staticmethod
    def entry_free(maxlen, w, _, t, beg, sz):
        return '   * free: (%s)' % part.bytes2str(sz * t.sectorsize)

    def entry_text(self, e, width):
        return { EntryType.Table:     self.entry_table,
                 EntryType.Partition: self.entry_partition,
                 EntryType.Free:      self.entry_free,
               }.get(e[0])(self.tab_longest+2, width, *e)

    def draw(self):
        Main   = self.Main
        width  = self.width
        height = self.height
        win    = self.win

        win.clear()

        count  = len(self.tab_entries)

        rectangle(win, 0, 0, height-1, width)
        win.addstr(0, 3, '[Partitioning]')

        height -= 2
        if self.tab_pos < self.tab_scroll:
            self.tab_scroll = self.tab_pos
        elif self.tab_scroll < self.tab_pos - height +1:
            self.tab_scroll = self.tab_pos - height +1

        x = 1
        y = 1
        eindex   = 0
        selected = self.tab_pos - self.tab_scroll
        for i in range(self.tab_scroll, count):
            if y > height:
                break
            ent = self.tab_entries[i]
            txt = self.entry_text(ent, width)
            if eindex == selected:
                attr = curses.A_REVERSE
            else:
                attr = curses.A_NORMAL
            win.addstr(y, x, txt, attr)
            eindex += 1
            y      += 1
        win.refresh()
