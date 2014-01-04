import part
import utils
from geom import geom

import curses
from curses.textpad import Textbox, rectangle

import gettext
L = gettext.gettext

class EntryType:
    Table     = 0
    Partition = 1
    Free      = 2

class ActionEnum:
    def __init__(self, default, pairs):
        self.default = default
        self.list_ = []

        for p in pairs:
            self.add(*p)

    def add(self, name, text):
        setattr(self, name, len(self.list_))
        self.list_.append('[%s]' % text)

    def get(self):
        return self.list_

TableActions     = ActionEnum(None, [('None',   L("Choose Partition"))])
PartitionActions = ActionEnum(0,    [('Use',    L("Use")),
                                     ('Delete', L("Delete Partition")),
                                    ])
FreeActions      = ActionEnum(0,    [('New',    L("Create Partition"))])

Window = utils.Window
class Parted(Window):
    def __init__(self, Main):
        Window.__init__(self, Main)
        self.notab = True

        self.Main       = Main
        self.tab_pos    = 0
        self.tab_scroll = 0

        self.act_pos    = None
        self.actions    = [ '' ]

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
        self.set_actions()

    def set_actions(self):
        ent          = self.tab_entries[self.tab_pos]
        if ent[0] == EntryType.Table:
            self.act_pos = TableActions.default
            self.actions = TableActions.get()
        elif ent[0] == EntryType.Partition:
            self.act_pos = PartitionActions.default
            self.actions = PartitionActions.get()
        elif ent[0] == EntryType.Free:
            self.act_pos = FreeActions.default
            self.actions = FreeActions.get()
        else:
            raise Exception('invalid table entry type')

    def select_action(self, relative):
        if self.act_pos is None:
            return
        self.act_pos += relative
        self.act_pos = max(0, min(len(self.actions)-1, self.act_pos))
        self.draw()

    def selection_changed(self):
        self.set_actions()
        self.draw()

    def event(self, key, name):
        maxpos = len(self.tab_entries)-1
        if utils.isk_down(key, name):
            # Down
            self.tab_pos = min(self.tab_pos+1, maxpos)
            self.selection_changed()
        elif utils.isk_up(key, name):
            # Up
            self.tab_pos = max(self.tab_pos-1, 0)
            self.selection_changed()
        elif utils.isk_home(key, name):
            # Top:
            self.tab_pos = 0
            self.selection_changed()
        elif utils.isk_end(key, name):
            # Bottom:
            self.tab_pos = maxpos
            self.selection_changed()
        elif utils.isk_scrolldown(key, name):
            # scroll down
            self.tab_scroll = min(self.tab_scroll+1, maxpos)
            self.selection_changed()
        elif utils.isk_scrollup(key, name):
            # scroll up
            self.tab_scroll = max(self.tab_scroll-1, 0)
            self.selection_changed()
        elif utils.isk_pagedown(key, name):
            # page down
            if self.tab_pos != self.tab_scroll + self.height - 3:
                self.tab_pos = self.tab_scroll + self.height - 3
            else:
                self.tab_pos += self.height-3
            self.tab_pos = min(maxpos, max(0, self.tab_pos))
            self.selection_changed()
        elif utils.isk_pageup(key, name):
            # page up
            if self.tab_pos != self.tab_scroll:
                self.tab_pos = self.tab_scroll
            else:
                self.tab_pos -= self.height-3
            self.tab_pos = min(maxpos, max(0, self.tab_pos))
            self.selection_changed()
        elif utils.isk_tab(key, name) or utils.isk_right(key, name):
            # tab/right: select next action
            self.select_action(1)
        elif utils.isk_left(key, name):
            # left / previous action
            self.select_action(-1)
        elif utils.isk_enter(key, name):
            self.action()
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

        # -2 for the rectangle borders
        height -= 2

        # -1 for the action line
        act_line = height
        height -= 1
        win.hline(height,     1, curses.ACS_HLINE, width-1)
        win.addch(height,     0, curses.ACS_LTEE)
        win.addch(height, width, curses.ACS_RTEE)
        # -1 for the action line's border
        height -= 1

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

        # show the action line...
        x = 2
        y = act_line
        for i in range(len(self.actions)):
            a = self.actions[i]
            if i == self.act_pos:
                attr = curses.A_REVERSE
            else:
                attr = curses.A_NORMAL
            win.addstr(y, x, a, attr)
            x += len(a) + 2

        win.refresh()

    def action(self):
        # see if there's even an action available
        if self.act_pos is None:
            return

        ent = self.tab_entries[self.tab_pos]
        if ent[0] == EntryType.Free:
            self.action_free(ent[1], ent[2], ent[3])
        elif ent[0] == EntryType.Partition:
            self.action_part(ent[1], ent[2])

    def action_free(self, table, start, size):
        self.draw()
        if self.act_pos == FreeActions.New:
            minsz  = table.sectorsize
            start *= table.sectorsize
            size  *= table.sectorsize
            partype = geom.partition_type_for(table.scheme, 'freebsd-ufs')
            with utils.Dialog(self.Main, L('New Partition'),
                              (('label', str,        '',      None),
                               ('start', utils.Size, start,   (0, size)),
                               ('size',  utils.Size, size,    (minsz, size)),
                               ('type',  str,        partype, None)
                              )) as dlg:
                result = dlg.run()
                if result is None:
                    return

                # convert to table sectors
                label  = result[0][2]
                ustart = part.str2bytes(result[1][2])
                usize  = part.str2types(result[2][2])
                ty     = result[3][2]
                ustart = max(ustart, start)
                usize  = min(usize,  size)
                msg = part.create_partition(table, label, ustart, usize, ty)
                if msg is not None:
                    utils.Message(self.Main, "Error", msg)
                else:
                    self.load()


    def action_part(self, table, part):
        self.draw()

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
