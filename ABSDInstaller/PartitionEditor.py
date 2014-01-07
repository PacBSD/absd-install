"""
ArchBSD Partition Editor UI.
"""

import curses
from curses.textpad import rectangle

import gettext
L = gettext.gettext

from . import utils, part
from geom import geom

class Entry(object):
    """A Partition entry. Has a set of allowed actions, a default action,
    and provides a formatting function."""
    # pylint: disable=too-few-public-methods
    def __init__(self, actions):
        self.actions = actions
        self.default = 0
        self.entry_text = lambda: '<missing entry_text implementation>'

    #def entry_text(parted, maxlen, win_width, data):

# pylint: disable=invalid-name
TableActions     = Entry([('act_table_destroy', L("Destroy Partition Table"))])
PartitionActions = Entry([('act_part_use',      L("Use")),
                          ('act_part_unuse',    L("Don't use")),
                          ('act_part_delete',   L("Delete Partition")),
                         ])
FreeActions      = Entry([('act_create_part',   L("Create Partition"))])
DiskActions      = Entry([('act_disk_setup',    L("Setup Partition Table"))])
# pylint: enable=invalid-name

Window = utils.Window
class PartitionEditor(Window):
    """Partition editor window class."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, app):
        Window.__init__(self, app)
        self.result = True
        self.flags.append(Window.NO_TAB)

        self.tab_pos     = 0
        self.tab_scroll  = 0
        self.tab_entries = []
        self.tab_longest = 0

        self.tables = []
        self.unused = []

        self.act_pos     = None
        self.actions     = [ '' ]

        self.width  = 0
        self.height = 0

        self.__load()
        self.resize()

    def resize(self):
        self.height = self.app.size[0] - 1
        self.width  = self.app.size[1] - 1
        self.win.resize(*self.app.size)
        self.win.mvwin(0, 0)

    def __iterate(self):
        """Entry generator function"""
        # pylint: disable=invalid-name
        self.tab_longest = 0
        for tab in self.tables:
            self.tab_longest = max(self.tab_longest, len(tab.name))
            yield (TableActions, (tab,))
            at = tab.first
            for p in tab.partitions:
                if p.start > at:
                    yield (FreeActions, (tab, at, p.start - at))
                self.tab_longest = max(self.tab_longest, len(p.name))
                yield (PartitionActions, (tab, p))
                at = p.end + 1
            if at < tab.last:
                yield (FreeActions, (tab, at, tab.last - at))
        for u in self.unused:
            yield (DiskActions, (u,))

    def __load(self):
        """Load the disk geometry, setup its entry tuples, clamp the selection
        position and update the available actions."""
        self.win.clear()
        self.tables, self.unused = part.load()
        self.tab_entries = list(self.__iterate())
        self.tab_pos     = min(self.tab_pos, len(self.tab_entries)-1)
        self.__set_actions()

    def __set_actions(self):
        """Pull the current entry's actions into self.actions and set act_pos
        to point to their default action."""
        ent = self.tab_entries[self.tab_pos]
        self.act_pos = ent[0].default
        self.actions = ent[0].actions

    def __select_action(self, relative, wrap=False):
        """Move in the action-button line, optionally wrapping around (usually
        when using the tab key). Causes a redraw when a change occurs."""
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

    def __selection_changed(self):
        """Callback to update the actions and redraw the window when the
        selection is changed."""
        self.__set_actions()
        self.draw()

    def event(self, key, name):
        # pylint: disable=too-many-branches
        maxpos = len(self.tab_entries)-1
        if name == b'q':
            return False
        elif utils.isk_down(key, name):
            # Down
            self.tab_pos = min(self.tab_pos+1, maxpos)
            self.__selection_changed()
        elif utils.isk_up(key, name):
            # Up
            self.tab_pos = max(self.tab_pos-1, 0)
            self.__selection_changed()
        elif utils.isk_home(key, name):
            # Top:
            self.tab_pos = 0
            self.__selection_changed()
        elif utils.isk_end(key, name):
            # Bottom:
            self.tab_pos = maxpos
            self.__selection_changed()
        elif utils.isk_scrolldown(key, name):
            # scroll down
            self.tab_scroll = min(self.tab_scroll+1, maxpos)
            self.__selection_changed()
        elif utils.isk_scrollup(key, name):
            # scroll up
            self.tab_scroll = max(self.tab_scroll-1, 0)
            self.__selection_changed()
        elif utils.isk_pagedown(key, name):
            # page down
            if self.tab_pos != self.tab_scroll + self.height - 3:
                self.tab_pos = self.tab_scroll + self.height - 3
            else:
                self.tab_pos += self.height-3
            self.tab_pos = min(maxpos, max(0, self.tab_pos))
            self.__selection_changed()
        elif utils.isk_pageup(key, name):
            # page up
            if self.tab_pos != self.tab_scroll:
                self.tab_pos = self.tab_scroll
            else:
                self.tab_pos -= self.height-3
            self.tab_pos = min(maxpos, max(0, self.tab_pos))
            self.__selection_changed()
        elif utils.isk_tab(key, name) or utils.isk_right(key, name):
            # tab/right: select next action
            self.__select_action(1, wrap=utils.isk_tab(key, name))
        elif utils.isk_left(key, name):
            # left / previous action
            self.__select_action(-1)
        elif utils.isk_enter(key, name):
            self.__action()
        return True

    def entry_text(self, entry, width):
        """Format an entry's text representation appropriately."""
        return entry[0].entry_text(self, self.tab_longest+2, width, entry)

    @utils.drawmethod
    def draw(self):
        # pylint: disable=too-many-locals
        width  = self.width
        height = self.height
        win    = self.win

        win.clear()

        count  = len(self.tab_entries)

        rectangle(win, 0, 0, height-1, width)
        win.addstr(0, 3, '[%s]' % L('Partition Editor'))

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
            win.addstr(0,        width - 16, utils.MORE_UP)
        if self.tab_scroll + height < count:
            win.addstr(height+1, width - 16, utils.MORE_DOWN)

        # pylint: disable=invalid-name
        x = 1
        y = 1
        eindex   = 0
        selected = self.tab_pos - self.tab_scroll
        for i in range(self.tab_scroll, count):
            if y > height:
                break
            ent, edata = self.tab_entries[i]
            # pylint: disable=star-args
            txt = ent.entry_text(self, self.tab_longest+2, width, *edata)
            win.addstr(y, x, txt, utils.highlight_if(eindex == selected))
            eindex += 1
            y      += 1

        # show the action line...
        x = 2
        y = act_line
        for i in range(len(self.actions)):
            a = self.actions[i][1]
            win.addstr(y, x, a, utils.highlight_if(i == self.act_pos))
            x += len(a) + 2

    def __action(self):
        """Perform the selected action if any."""
        # see if there's even an action available
        if self.act_pos is None:
            return

        entry, data = self.tab_entries[self.tab_pos]
        method  = entry.actions[self.act_pos][0]
        func    = getattr(self, method)
        # pylint: disable=star-args
        func(*data)
        self.draw()

    def act_table_destroy(self, table):
        """Destroy a partition table: equivalent of gpart destroy"""
        text = ((L("Do you want to destroy %s?\n") % table.name)
               + L("WARNING: THIS OPERATION CANNOT BE UNDONE!")
               )
        if utils.no_yes(self.app, L("Destroy Table?"), text):
            msg = part.destroy_partition_table(table)
            if msg is not None:
                utils.message(self.app, L("Error"), msg)
            else:
                self.__load()

    def act_disk_setup(self, provider):
        """Create a partition table: equivalent of gpart create"""
        with utils.Dialog(self.app, L('New Partition Table'),
                          [('scheme', str, 'GPT', None)]) as dlg:
            dlg.flags.append(Window.ENTER_ACCEPTS)
            result = dlg.run()
            if result is None:
                return
            msg = part.create_partition_table(provider, result[0][2])
            if msg is not None:
                utils.message(self.app, L("Error"), msg)
            else:
                self.__load()

    def act_create_part(self, table, start, size):
        """Create a partition: equivalent of gpart add"""
        minsz  = table.sectorsize
        start *= table.sectorsize
        size  *= table.sectorsize
        partype = geom.partition_type_for(table.scheme, 'freebsd-ufs')
        with utils.Dialog(self.app, L('New Partition'),
                          [('label', utils.Label, '',      None),
                           ('start', utils.Size,  start,   (0, size)),
                           ('size',  utils.Size,  size,    (minsz, size)),
                           ('type',  str,         partype, None)
                          ]) as dlg:
            result = dlg.run()
            if result is None:
                return

            # convert to table sectors
            label  = result[0][2]
            ustart = part.str2bytes(result[1][2])
            usize  = part.str2bytes(result[2][2])
            type_  = result[3][2]
            ustart = max(ustart, start)
            usize  = min(usize,  size)
            msg = part.create_partition(table, label, ustart, usize, type_)
            if msg is not None:
                utils.message(self.app, L("Error"), msg)
            else:
                self.__load()

    def act_part_delete(self, _, partition):
        """Delete a partition: equivalent of gpart delete"""
        text = ((L("Do you want to delete partition %s?\n") % partition.name)
               + L("WARNING: THIS OPERATION CANNOT BE UNDONE!")
               )
        if utils.no_yes(self.app, L("Delete Partition?"), text):
            msg = self.__delete_partition(partition)
            if msg is not None:
                utils.message(self.app, L("Error"), msg)
            else:
                self.__load()

    def act_part_use(self, _, partition):
        """Set a partition to be used: its mountpoint or bootcode property."""
        point = self.suggest_mountpoint(partition)
        with utils.Dialog(self.app, L('Use Partition %s') % partition.name,
                          [('Mountpoint', str, point, None)]
                         ) as dlg:
            dlg.flags.append(Window.ENTER_ACCEPTS)
            result = dlg.run()
            if result is None:
                return

            self.__set_mountpoint(partition, result[0][2])

    def act_part_unuse(self, _, partition):
        """Ask for confirmation and then calls unuse() on the selected
        partition so it is not used as mountpoint in fstab, and not used
        to install bootcode to."""
        usage = self.used_as(partition)
        if usage is None:
            return
        text = L('Stop using partition %s?') % partition.name
        if utils.yes_no(self.app, text, '%s\n%s' % (text, usage)):
            self.__unuse(partition.name)

    def __unuse(self, partname):
        """Performs the actual task of making a partition not being used as
        a mountpoint or for bootcode installation."""
        if self.app.bootcode == partname:
            self.app.bootcode = ''
        try:
            del self.app.fstab[partname]
        except KeyError:
            pass

    def __delete_partition(self, partition):
        """Perform the actual partition deletion: gpart delete"""
        self.__unuse(partition.name)
        msg = part.delete_partition(partition)
        if msg is not None:
            return msg

    def used_as(self, partition):
        """Get a textual representation of what the partition is being used as,
        or None if it's not being used."""
        fstab = self.app.fstab.get(partition.name, None)
        if fstab is None:
            if self.app.bootcode == partition.name:
                return '<bootcode>'
            else:
                return None
        else:
            return 'mountpoint: %s' % fstab['mount']
        return None

    def __set_mountpoint(self, partition, point):
        """Set the mountpoint of a partition. This will cause it to be added
        to /etc/fstab if necessary.
        The special value '*bootcode' causes the installer to install bootcode
        to the partition (gpart bootcode)."""
        if point is None or len(point) == 0:
            return self.__unuse(partition.name)

        if point == '*bootcode':
            self.app.bootcode = partition.name
            return

        self.app.fstab[partition.name] = {
            'mount': point
        }

    def suggest_mountpoint(self, partition):
        """Suggest a mountopint for a partition.

        For a freebsd-boot partition (or a 'freebsd' partition, like on MBR
        setups where they cannot be distinguished, which is smaller than 8M.).

        For a freebsd-swap partition, this will return 'swap'. (On MBR setups,
        this will be returned if all other suggestions are already in use and
        the partition is <= 9G in size.)

        Otherwise if the partition is already being used, its current use is
        returned.

        For any other partitions, the following suggestions will appear in
        order (if they are not already used.):
        1) /
        2) /home
        """
        # pylint: disable=too-many-return-statements

        if partition.partype == 'freebsd-swap':
            return 'swap'
        if partition.partype == 'freebsd-boot':
            return '*bootcode'

        old = self.app.fstab.get(partition.name, None)
        if old is not None:
            return old['mount']

        suggestions = [ '/', '/home' ]
        current = 0
        for _, value in self.app.fstab.items():
            if value['mount'] == suggestions[current]:
                current += 1
                if current >= len(suggestions):
                    break
        if current < len(suggestions):
            return suggestions[current]

        if partition.partype == 'freebsd': # MBR has no -swap etc
            if partition.bytes_ <= 9*1024*1024*1024:
                return 'swap'
            if partition.bytes_ <= 8*1024*1024:
                return '*bootcode'

        return ''

    def before_close(self):
        """When there are pending geom changes, ask whether they should be
        committed or rolled back before quitting.
        Note that the rollback happens automatically in atexit."""
        if len(geom.Uncommitted):
            msg = L("Do you want to commit your changes"
                    " to the following disks?\n") + ', '.join(geom.Uncommitted)
            if utils.no_yes(self.app, L("Commit changes?"), msg):
                geom.geom_commit_all()


def text_entry_table(unused_self, maxlen, unused_win_width, table):
    """text representation for a disk with partition table"""
    # pylint: disable=unused-argument
    return '%s%s    %s [%s]' % (table.name,
                                ' ' * (maxlen - len(table.name)),
                                table.scheme,
                                part.bytes2str(table.size))
TableActions.entry_text = text_entry_table

def text_entry_free(self, maxlen, win_width, table, beg, size):
    """text representation for free space on a disk"""
    # pylint: disable=unused-argument
    # pylint: disable=too-many-arguments
    return '   * free: (%s)' % part.bytes2str(size * table.sectorsize)
FreeActions.entry_text = text_entry_free

def text_entry_partition(self, maxlen, win_width, table, partition):
    """text representation for a partition"""
    # pylint: disable=unused-argument
    bytestr = part.bytes2str(partition.bytes_)
    usage   = self.used_as(partition)
    if usage is None:
        usage = ''
    return '  => %s%s%- 14s [%s] %s' % (partition.name,
                                        ' ' * (maxlen - len(partition.name)),
                                        partition.partype,
                                        bytestr,
                                        usage)
PartitionActions.entry_text = text_entry_partition

def text_entry_disk(self, maxlen, win_width, provider):
    """text representation for a disk without a partition table"""
    # pylint: disable=unused-argument
    size = part.bytes2str(provider.mediasize)
    return 'disk: %s [%s]' % (provider.name, size)
DiskActions.entry_text = text_entry_disk
