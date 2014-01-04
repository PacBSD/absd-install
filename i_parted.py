import part
import utils
from geom import geom

import curses
from curses.textpad import Textbox, rectangle

import gettext
L = gettext.gettext

class ActionEnum:
    def __init__(self, default, pairs):
        self.default = default
        self.actions = []

        for p in pairs:
            self.add(*p)

    def add(self, name, text):
        setattr(self, name, len(self.actions))
        self.actions.append('[%s]' % text)

    def get(self):
        return self.list_

TableEntry     = ActionEnum(None, [('None',   L("Choose Partition"))])
PartitionEntry = ActionEnum(0,    [('Use',    L("Use")),
                                   ('Unuse',  L("Do not use")),
                                   ('Delete', L("Delete Partition")),
                                  ])
FreeEntry      = ActionEnum(0,    [('New',    L("Create Partition"))])
EmptyEntry     = ActionEnum(0,    [('New',    L("Setup Partition Table"))])

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
            yield (TableEntry, t)
            at = t.first
            for p in t.partitions:
                if p.start > at:
                    yield (FreeEntry, t, at, p.start - at)
                self.tab_longest = max(self.tab_longest, len(p.name))
                yield (PartitionEntry, t, p)
                at = p.end + 1
            if at < t.last:
                yield (FreeEntry, t, at, t.last - at)
        for u in self.unused:
            yield (EmptyEntry, u)

    def load(self):
        self.win.clear()
        self.tables, self.unused = part.load()
        self.tab_entries = [i for i in self.iterate()]
        self.tab_pos     = min(self.tab_pos, len(self.tab_entries)-1)
        self.set_actions()

    def set_actions(self):
        ent = self.tab_entries[self.tab_pos]
        self.act_pos = ent[0].default
        self.actions = ent[0].actions

    def select_action(self, relative, wrap=False):
        if self.act_pos is None:
            return
        self.act_pos += relative
        if wrap:
            if self.act_pos < 0:
                self.act_pos = len(self.actions)-1
            elif self.act_pos >= len(self.actions):
                self.act_pos = 0
        else:
            self.act_pos = max(0, min(len(self.actions)-1, self.act_pos))
        self.draw()

    def selection_changed(self):
        self.set_actions()
        self.draw()

    def event(self, key, name):
        maxpos = len(self.tab_entries)-1
        if name == b'q':
            return False
        elif utils.isk_down(key, name):
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
            self.select_action(1, wrap=utils.isk_tab(key, name))
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
    def entry_free(maxlen, w, _, t, beg, sz):
        return '   * free: (%s)' % part.bytes2str(sz * t.sectorsize)

    # used to be static but now we need access to self.Main
    def entry_partition(self, maxlen, w, _, t, p):
        bytestr = part.bytes2str(p.bytes_)
        usage   = self.used_as(p)
        if usage is None:
            usage = ''
        return '  => %s%s%- 14s [%s] %s' % (p.name,
                                         ' ' * (maxlen - len(p.name)),
                                         p.partype,
                                         bytestr,
                                         usage)

    @staticmethod
    def entry_empty(maxlen, w, _, provider):
        size = part.bytes2str(provider.mediasize)
        return 'disk: %s [%s]' % (provider.name, size)

    def entry_text(self, e, width):
        for i in [(TableEntry,     self.entry_table),
                  (FreeEntry,      self.entry_free),
                  (PartitionEntry,
                        lambda a,b,c,d,e: self.entry_partition(a,b,c,d,e)),
                  (EmptyEntry,     self.entry_empty)]:
            if i[0] == e[0]:
                return i[1](self.tab_longest+2, width, *e)
        raise Exception('invalid entry type')

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
        if ent[0] == FreeEntry:
            self.action_free(ent[1], ent[2], ent[3])
        elif ent[0] == PartitionEntry:
            self.action_part(ent[1], ent[2])
        elif ent[0] == EmptyEntry:
            self.action_empty(ent[1])

    def action_empty(self, provider):
        if self.act_pos == EmptyEntry.New:
            with utils.Dialog(self.Main, L('New Partition Table'),
                              [('scheme', str, 'GPT', None)]) as dlg:
                dlg.enter_accepts = True
                result = dlg.run()
                if result is None:
                    self.draw()
                    return
                msg = part.create_partition_table(provider, result[0][2])
                if msg is not None:
                    utils.Message(self.Main, L("Error"), msg)
                else:
                    self.load()
            self.draw()

    def action_free(self, table, start, size):
        if self.act_pos == FreeActions.New:
            minsz  = table.sectorsize
            start *= table.sectorsize
            size  *= table.sectorsize
            partype = geom.partition_type_for(table.scheme, 'freebsd-ufs')
            with utils.Dialog(self.Main, L('New Partition'),
                              [('label', utils.Label, '',      None),
                               ('start', utils.Size,  start,   (0, size)),
                               ('size',  utils.Size,  size,    (minsz, size)),
                               ('type',  str,         partype, None)
                              ]) as dlg:
                result = dlg.run()
                if result is None:
                    self.draw()
                    return

                # convert to table sectors
                label  = result[0][2]
                ustart = part.str2bytes(result[1][2])
                usize  = part.str2bytes(result[2][2])
                ty     = result[3][2]
                ustart = max(ustart, start)
                usize  = min(usize,  size)
                msg = part.create_partition(table, label, ustart, usize, ty)
                if msg is not None:
                    utils.Message(self.Main, L("Error"), msg)
                else:
                    self.load()
            self.draw()

    def action_part(self, table, p):
        if self.act_pos == PartitionActions.Delete:
            text = ((L("Do you want to delete partition %s?\n") % p.name)
                   + L("WARNING: THIS OPERATION CANNOT BE UNDONE!")
                   )
            if utils.NoYes(self.Main, L("Delete Partition?"), text):
                msg = self.delete_partition(p)
                if msg is not None:
                    utils.Message(self.Main, L("Error"), msg)
                else:
                    self.load()

        elif self.act_pos == PartitionActions.Use:
            point = self.suggest_mountpoint(p)
            with utils.Dialog(self.Main, L('Use Partition %s') % p.name,
                              [('Mountpoint', str, point, None)]
                             ) as dlg:
                dlg.enter_accepts = True
                result = dlg.run()
                if result is None:
                    self.draw()
                    return

                self.set_mountpoint(p, result[0][2])

        elif self.act_pos == PartitionActions.Unuse:
            usage = self.used_as(p)
            if usage is None:
                return
            text = L('Stop using partition %s?') % p.name
            if utils.YesNo(self.Main, text, '%s\n%s' % (text, usage)):
                self.unuse(p.name)

        self.draw()

    def unuse(self, partname):
        if self.Main.bootcode == partname:
            self.Main.bootcode = ''
        try:
            del self.Main.fstab[partname]
        except:
            pass

    def delete_partition(self, p):
        self.unuse(p.name)
        msg = part.delete_partition(p)
        if msg is not None:
            return msg

    def used_as(self, part):
        fstab = self.Main.fstab.get(part.name, None)
        if fstab is None:
            if self.Main.bootcode == part.name:
                return '<bootcode>'
            else:
                return None
        else:
            return 'mountpoint: %s' % fstab['mount']
        return None

    def set_mountpoint(self, part, point):
        if point is None or len(point) == 0:
            return self.unuse(part.name)

        if point == '*bootcode':
            self.Main.bootcode = part.name
            return

        self.Main.fstab[part.name] = {
            'mount': point
        }

    def suggest_mountpoint(self, part):
        if part.partype == 'freebsd-swap':
            return 'swap'
        if part.partype == 'freebsd-boot':
            return '*bootcode'

        old = self.Main.fstab.get(part.name, None)
        if old is not None:
            return old['mount']

        suggestions = [ '/', '/home' ]
        current = 0
        for k,v in self.Main.fstab:
            if k == suggestions[current]:
                current += 1
                if current >= len(suggestions):
                    break
        if current < len(suggestions):
            return suggestions[current]

        if part.partype == 'freebsd': # MBR has no -swap etc
            if part.bytes_ <= 9*1024*1024*1024:
                return 'swap'
            if part.bytes_ <= 8*1024*1024:
                return '*bootcode'

        return ''

    def before_close(self):
        if len(geom.Uncommitted):
            msg = L(
"Do you want to commit your changes to the following disks?\n"
                   ) + ', '.join(geom.Uncommitted)
            if utils.NoYes(self.Main, L("Commit changes?"), msg):
                geom.geom_commit_all()
