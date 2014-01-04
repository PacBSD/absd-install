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
        if utils.isk_down(key, name):
            # Down
            self.tab_pos = min(self.tab_pos+1, maxpos)
            self.draw()
        elif utils.isk_up(key, name):
            # Up
            self.tab_pos = max(self.tab_pos-1, 0)
            self.draw()
        elif utils.isk_home(key, name):
            # Top:
            self.tab_pos = 0
            self.draw()
        elif utils.isk_end(key, name):
            # Bottom:
            self.tab_pos = maxpos
            self.draw()
        elif utils.isk_scrolldown(key, name):
            # scroll down
            self.tab_scroll = min(self.tab_scroll+1, maxpos)
            self.draw()
        elif utils.isk_scrollup(key, name):
            # scroll up
            self.tab_scroll = max(self.tab_scroll-1, 0)
            self.draw()
        elif utils.isk_pagedown(key, name):
            # page down
            if self.tab_pos != self.tab_scroll + self.height - 3:
                self.tab_pos = self.tab_scroll + self.height - 3
            else:
                self.tab_pos += self.height-3
            self.tab_pos = min(maxpos, max(0, self.tab_pos))
            self.draw()
        elif utils.isk_pageup(key, name):
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
        elif self.tab_scroll < self.tab_pos - height + 1:
            self.tab_scroll =  self.tab_pos - height + 1

        if self.tab_scroll > 0:
            win.addstr(0,        width - 16, ' [ ^^^ more ] ')
        if self.tab_scroll + height < count:
            win.addstr(height+1, width - 16, ' [ vvv more ] ')

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

def partition_action():
    if Main.tables_sel is None:
        return
    (text, entry) = Main.tables_sel
    if entry[0] == EntryType.Table:
        Main.status_msg = "Partition Table actions not implemented"
        draw_gui()
    elif entry[0] == EntryType.Partition:
        (_, table, partition) = entry
        with utils.YesNo(Main, "Delete Partition",
                         "Do you want to delete partition %s?" % partition.name
                        ) as dlg:
            dlg.current = 1
            res = dlg.run()
            if res:
                Main.status_msg = part.delete_partition(partition)
            draw_gui()
    elif entry[0] == EntryType.Free:
        (_, table, start, size) = entry

        #start = start * table.sectorsize
        #end   = start + size * table.sectorsize
        end    = start + size
        start *= table.sectorsize
        end   *= table.sectorsize
        size   = str(end - start)

        partype = geom.partition_type_for(table.scheme, 'freebsd-ufs')

        with utils.Dialog(Main, "New Partition",
                          (('label', str,        '',      None),
                           ('start', utils.Size, start,   (0, end-start)),
                           ('size',  utils.Size, size,    (0, end-start)),
                           ('type',  str,        partype, None)
                          )) as dlg:
            result = dlg.run()
            if result is not None:
                label, ustart, usize, ty = result
                bstart = part.str2bytes(ustart[2])
                bsize  = part.str2bytes(usize[2])
                if bstart < start:
                    bstart = start
                if bsize > (end-start):
                    bsize = (end-start)
                msg = part.create_partition(table, label[2], bstart, bsize,
                                            ty[2])
                Main.status_msg = msg
            draw_gui()
    else:
        Main.status_msg = "(nothing to do)"
        draw_gui()
