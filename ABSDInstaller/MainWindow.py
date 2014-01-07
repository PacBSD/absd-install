"""
ArchBSD Installer main menu.

Allows the user to choose between the steps required to install the system,
one after the other. The user may skip a step, for instance if they already
did something manually.

The currently provided steps are:

    1) Keyboard Selection
         This is mostly useful if we decide to run the installer automatically
         or if the users doesn't yet know how to use kbdmap. It might however
         be better to start the iso off with an optional keyboard selection
         dialog.

    2) Partitioning
         Shows the partition editor. This mostly deals with boot and UFS
         partitions. ZFS support is minimal as it is quite complex. A basic ZFS
         configuration can be created (TODO), but no complex operations will be
         provided as a we assume that a user who knows about them is also
         capable of using the zpool/zfs CLI tools.
"""

from curses.textpad import rectangle

import gettext
L = gettext.gettext

from . import utils
from .KeyboardSelector import KeyboardSelector
from .PartitionEditor  import PartitionEditor

class MainWindow(utils.Window):
    """Main window"""
    def __init__(self, app):
        utils.Window.__init__(self, app)

        self.width  = 0
        self.height = 0

        self.title = L('Installer Main Menu')
        self.entries = [
            (L('Keyboard Selection'),  self.show_keymaps          ),
            (L('Partition Editor'),    self.show_parted           ),
            (L('Quit without saving'), lambda: self.exit(False)   ),
            (L('Exit and Save'),       lambda: self.exit(True)    ),
        ]
        self.tabcount = len(self.entries)
        self.longest = len(self.title)+6
        for title, _ in self.entries:
            self.longest = max(self.longest, len(title))

        self.resize()

    def resize(self):
        self.height = min(self.app.size[0] - 1, len(self.entries)+2)
        self.width  = min(self.app.size[1] - 1, self.longest+4)

        self.win.resize(self.height+1, self.width+1)
        self.center(self.height, self.width)

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
            return self.__action()

        return True

    def __action(self):
        """Execute the selected action."""
        _, action = self.entries[self.current]
        result = action()
        self.app.screen.erase()
        self.app.screen.refresh()
        return result

    def exit(self, save):
        """Exit the main dialog and optionally call the installer's save()
        method."""
        if save:
            self.app.save()
        return False

    def show_keymaps(self):
        """Show the keyboard selection window."""
        with KeyboardSelector(self.app) as keyboard:
            if keyboard.run() is None:
                return False
        return True

    def show_parted(self):
        """Show the partition editor."""
        with PartitionEditor(self.app) as parted:
            if parted.run() is None:
                return False
        return True

    @utils.drawmethod
    def draw(self):
        width  = self.width
        height = self.height
        win    = self.win

        # pylint: disable=invalid-name
        y = 1
        x = 2
        for i in range(self.tabcount):
            text, _ = self.entries[i]
            win.addstr(y, x, text, utils.highlight_if(i == self.current))
            y += 1

        rectangle(win, 0, 0, height-1, width)
        win.addstr(0, 3, '[%s]' % self.title)
