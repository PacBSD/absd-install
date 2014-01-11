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
TableActions     = Entry([('__table_destroy', L("Destroy Partition Table")),
                          ('__table_boot',    L("Choose Bootcode"))])
PartitionActions = Entry([('__part_use',      L("Use")),
                          ('__part_unuse',    L("Don't use")),
                          ('__part_delete',   L("Delete Partition")),
                          ('__part_boot',     L("Choose Bootcode")),
                         ])
FreeActions      = Entry([('__part_create',   L("Create Partition"))])
DiskActions      = Entry([('__disk_setup',    L("Setup Partition Table"))])
# pylint: enable=invalid-name

Window = utils.Window
class PartitionEditor(Window):
    """Partition editor window class."""

    def __init__(self, app):
        Window.__init__(self, app)
        self.flags.append(Window.NO_TAB)

        self.partlist    = utils.List(self, (0, 0))
        self.partlist.name   = L('Partition Editor')
        self.partlist.border = False
        self.partlist.selection_changed = self.__selection_changed

        self.tables      = []
        self.unused      = []
        self.zpools      = []

        self.act_pos     = None
        self.actions     = [ '' ]

        self.__load()
        self.resize()

    def resize(self):
        self.size = (self.app.size[0], self.app.size[1])
        self.win.resize(*self.size)
        self.win.mvwin(0, 0)
        self.partlist.size = (self.size[0] - 1, self.size[1])

    def __iterate(self):
        """Entry generator function"""
        tab_longest = 0
        for tab in self.tables:
            tab_longest = max(tab_longest, len(tab.name))
            yield (TableActions, (tab,))
            sector = tab.first
            for par in tab.partitions:
                if par.start > sector:
                    yield (FreeActions, (tab, sector, par.start - sector))
                tab_longest = max(tab_longest, len(par.name))
                yield (PartitionActions, (tab, par))
                sector = par.end + 1
            if sector < tab.last:
                yield (FreeActions, (tab, sector, tab.last - sector))
        for unused in self.unused:
            yield (DiskActions, (unused,))
        self.partlist.userdata = tab_longest

    def __load(self):
        """Load the disk geometry, setup its entry tuples, clamp the selection
        position and update the available actions."""
        self.win.clear()
        self.tables, self.unused, self.zpools = part.load()
        self.partlist.entries = list(self.__iterate())
        self.__set_actions()

    def __set_actions(self):
        """Pull the current entry's actions into self.actions and set act_pos
        to point to their default action."""
        ent = self.partlist.entry()
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
        if name == b'q':
            return False
        elif (utils.isk_down      (key, name) or
              utils.isk_up        (key, name) or
              utils.isk_home      (key, name) or
              utils.isk_end       (key, name) or
              utils.isk_scrolldown(key, name) or
              utils.isk_scrollup  (key, name) or
              utils.isk_pagedown  (key, name) or
              utils.isk_pageup    (key, name)
             ):
            self.partlist.event(key, name)
        elif utils.isk_tab(key, name) or utils.isk_right(key, name):
            # tab/right: select next action
            self.__select_action(1, wrap=utils.isk_tab(key, name))
        elif utils.isk_left(key, name):
            # left / previous action
            self.__select_action(-1)
        elif utils.isk_enter(key, name):
            self.__action()
        return True

    @utils.drawmethod
    def draw(self):
        height, width = self.size
        win    = self.win

        win.clear()

        self.partlist.draw()

        height -= 3
        width -= 1

        # pylint: disable=no-member
        #  it doesn't seem to get the ACS_* constants in curses
        utils.rectangle(win, height, 0, height+2, width)
        win.addch(height,       0, curses.ACS_LTEE)
        win.addch(height,   width, curses.ACS_RTEE)

        # Show the current actions:

        # x and y: pylint: disable=invalid-name
        x = 2
        y = height+1
        for i in range(len(self.actions)):
            action = self.actions[i][1]
            win.addstr(y, x, action, utils.highlight_if(i == self.act_pos))
            x += len(action) + 2
        # pylint: enable=invalid-name

    def __action(self):
        """Perform the selected action if any."""
        # see if there's even an action available
        if self.act_pos is None:
            return

        entry, data = self.partlist.entry()
        method  = entry.actions[self.act_pos][0]
        func    = getattr(self, method)
        # pylint: disable=star-args
        func(*data)
        self.draw()

    def __table_destroy(self, table):
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

    def __act_bootcode(self, name, suggested):
        """Declare a bootcode to be written to a disk or partition."""
        with utils.Dialog(self.app, L('Set bootcode for %s') % name,
                          [('Bootcode', str, suggested, None)]
                         ) as dlg:
            dlg.flags.append(Window.ENTER_ACCEPTS)
            result = dlg.run()
            if result is None:
                return
            code = result[0][2]
            if len(code) == 0:
                code = None
            self.__set_bootcode(name, code)

    def __table_boot(self, table):
        """Set a disk's bootcode"""
        code = self.suggest_disk_bootcode(table)
        return self.__act_bootcode(table.name, code)

    def __disk_setup(self, provider):
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

    def __part_create(self, table, start, size):
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

    def __part_delete(self, _, partition):
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

    def __part_use(self, _, partition):
        """Set a partition's mount point"""
        point = self.suggest_mountpoint(partition)
        with utils.Dialog(self.app, L('Use Partition %s') % partition.name,
                          [('Mountpoint', str, point, None)]
                         ) as dlg:
            dlg.flags.append(Window.ENTER_ACCEPTS)
            result = dlg.run()
            if result is None:
                return

            self.__set_mountpoint(partition, result[0][2])

    def __part_boot(self, _, partition):
        """Set a partition's bootcode"""
        code = self.suggest_part_bootcode(partition)
        return self.__act_bootcode(partition.name, code)

    def __part_unuse(self, _, partition):
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
        for pool in self.zpools:
            if partition.name in pool.children:
                return 'zpool: %s' % pool.name
        fstab = self.app.fstab.get(partition.name, None)
        if fstab is not None:
            return 'mountpoint: %s' % fstab['mount']
        boot = self.app.bootcode.get(partition.name, None)
        if boot is not None:
            return 'bootcode: %s' % boot
        return None

    def __set_bootcode(self, name, code):
        """Set a partition's or disk's bootcode"""
        # set then delete, no 'is in' check then required :P (lame I know)
        self.app.bootcode[name] = code
        if code is None:
            del self.app.bootcode[name]

    def __set_mountpoint(self, partition, point):
        """Set the mountpoint of a partition. This will cause it to be added
        to /etc/fstab if necessary."""
        if point is None or len(point) == 0:
            return self.__unuse(partition.name)

        if point == '*bootcode':
            code = self.suggest_part_bootcode(partition)
            self.__set_bootcode(partition.name, code)
            return

        self.app.fstab[partition.name] = {
            'mount': point
        }

    @staticmethod
    def suggest_disk_bootcode(table):
        """Suggest a bootcode file for a disk with a partition table."""
        bclist = {
            'GPT': '/boot/pmbr',
            'MBR': '/boot/mbr',
            'EBR': '/boot/mbr',
        }
        return bclist.get(table.scheme, None)

    @staticmethod
    def suggest_part_bootcode(partition):
        """Suggest a bootcode file for a partition. Mainly depends on the
        partition table scheme."""
        bclist = {
            'GPT': '/boot/gptboot',
            'MBR': '/boot/boot',
            'EBR': '/boot/boot',
        }
        return bclist.get(partition.owner.scheme, None)

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


def text_entry_table(self, maxlen, unused_win_width, table):
    """text representation for a disk with partition table"""
    # pylint: disable=unused-argument
    usage   = self.app.bootcode.get(table.name, None)
    if usage is not None:
        usage = 'bootcode: %s' % usage
    else:
        usage = ''
    return '%s%s    %s [%s] %s' % (table.name,
                                   ' ' * (maxlen - len(table.name)),
                                   table.scheme,
                                   part.bytes2str(table.size),
                                   usage)
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
