"""
Utilities module.
Contains the Window class and some common subclasses.
Some localized strings, and functions for common key mappings.
(ie vim/emacs/arrow down/up/left/right key checks, see the isk_* functions).
"""

import curses
import string

import gettext
L = gettext.gettext

MORE_UP   = ' [ ^^^ %s ] ' % L('more')
MORE_DOWN = ' [ vvv %s ] ' % L('more')

class Size(object):
    """A byte-size type for an input field in Dialog."""
    # pylint: disable=too-few-public-methods
    @staticmethod
    def allowed(char, text, position):
        """common way to express a size is a number with an optional unit
        suffix like M for Megabytes. Also allow 0x for hex numbers."""
        # 0x prefix allowed:
        if len(text) > 1 and text[0] == '0' and position == 1 and char == 'x':
            return True
        if char == ',' or char == '.':
            # , is stripped and . is allowed
            return True
        if position == len(text) and char in 'kMGT':
            return True
        return char in string.digits

class Label(object):
    """Label type for the Dialog window. Restricts allowed characters."""
    # pylint: disable=too-few-public-methods
    # pylint: disable=unused-argument
    @staticmethod
    def allowed(char, unused_text, unused_position):
        """labels can be [a-zA-Z0-9_]"""
        return (char in string.ascii_letters or
                char in string.digits        or
                char in '_-')

def translate_key(key):
    """Remove the ValueError from curses.keyname"""
    try:
        return curses.keyname(key)
    except ValueError:
        return key

# vim/emacs/lame key checks:
def isk_up(key, name):
    """up-arrow, 'k' or ctrl+P"""
    return key == curses.KEY_UP   or name == b'k' or name == b'^P'

def isk_down(key, name):
    """down-arrow, 'j' or ctrl+N"""
    return key == curses.KEY_DOWN or name == b'j' or name == b'^N'

def isk_left(key, name):
    """left-arrow, 'h' or ctrl+B"""
    return key == curses.KEY_LEFT or name == b'h' or name == b'^B'

def isk_right(key, name):
    """right-arrow, 'l' or ctrl+F"""
    return key == curses.KEY_RIGHT or name == b'l' or name == b'^F'

def isk_home(key, name):
    """HOME key, 'g' or ctrl+A"""
    return key == curses.KEY_HOME or name == b'g' or name == b'^A'

# the emacs key binding here clashes with isk_scrolldown, make sure you test
# the more important one first...
def isk_end(key, name):
    """END key, 'G' or ctrl+E"""
    return key == curses.KEY_END  or name == b'G' or name == b'^E'

def isk_pageup(key, _):
    """page up key, currently no other variation"""
    return key == curses.KEY_PPAGE

def isk_pagedown(key, _):
    """page down key, currently no other variation"""
    return key == curses.KEY_NPAGE

def isk_scrollup(_, name):
    """vim-like up-scrolling with ctrl+Y"""
    return name == b'^Y'

def isk_scrolldown(_, name):
    """vim-like down-scrolling with ctrl+E"""
    return name == b'^E'

def isk_tab(_, name):
    """ctrl+I is the tab key"""
    return name == b'^I'

def isk_enter(key, name):
    """enter key or ctrl+M"""
    return key == curses.KEY_ENTER or name == b'^M'

def isk_backspace(key, name):
    """backspace or ctrl+H"""
    return key == curses.KEY_BACKSPACE or name == b'^H'

def isk_del(key, name):
    """DEL key or ctrl+D"""
    return key == curses.KEY_DC or name == b'^D'

def isk_del_to_front(_, name):
    """emacs-like cut-to-front with ctrl+U"""
    return name == b'^U'

def isk_del_to_end(_, name):
    """emacs-like kill-rest-of-line with ctrl+K"""
    return name == b'^K'

def isk_yank(_, name):
    """emacs-like yank with ctrl+Y"""
    return name == b'^Y'

def highlight_if(cond):
    """Return the highlighted background attribute if the condition is true,
    the normal one otherwise."""
    # Mostly because the inline 'curses.A_REVERSE if FOO else curses...'
    # doesn't very much like to fit in the 80 char column limit :P
    if cond:
        return curses.A_REVERSE
    return curses.A_NORMAL

# decorator
def drawmethod(func):
    """self.draw() methods want to call win.refresh when they leave, always."""
    def inner(self, *args, **kwargs):
        # pylint: disable=missing-docstring
        result = func(self, *args, **kwargs)
        self.win.refresh()
        return result
    return inner

# decorator
def redraw(func):
    """some methods modify the state and want to call self.draw() after
    returning regardless of which path they took.
    This is just code deduplication"""
    def inner(self, *args, **kwargs):
        # pylint: disable=missing-docstring
        result = func(self, *args, **kwargs)
        self.draw()
        return result
    return inner

def rectangle(win, uly, ulx, lry, lrx):
    """textpad.rectangle but without moving the cursor to outside the rectangle
    so that it can be used to put a rectangle onto the entire window without
    raising that stupid exception caused by its last .addch call..."""
    win.hline(uly, ulx, curses.ACS_HLINE, lrx - ulx)
    win.vline(uly, ulx, curses.ACS_VLINE, lry - uly)
    win.vline(uly, lrx, curses.ACS_VLINE, lry - uly)
    win.hline(lry, ulx, curses.ACS_HLINE, lrx - ulx)
    win.addch(uly, ulx, curses.ACS_ULCORNER)
    win.addch(uly, lrx, curses.ACS_URCORNER)
    win.addch(lry, ulx, curses.ACS_LLCORNER)
    win.delch(lry, lrx)
    win.insch(lry, lrx, curses.ACS_LRCORNER) # INSch!

class Window(object):
    """Window baseclass. Creates a curses window, by default intercepts TAB
    keys, handles input events and declares the default attributes.
    Provides __enter__ and __exit__ to be used in a 'with' statement.
    Provides empty draw functions."""

    NO_TAB        = 1
    ENTER_ACCEPTS = 2

    def __init__(self, app, tabcount=0, result=None):
        self.app      = app
        self.result   = result
        self.current  = 0
        self.tabcount = tabcount
        self.size     = (5, 5)
        self.win      = curses.newwin(5, 5)
        self.flags    = []

    def run(self):
        """Window's entrypoint:
        calls self.resize, self.draw, and starts the event loop, returns
        self.result"""
        self.resize()
        self.draw()
        try:
            while self.event_p(*self.app.get_key()):
                pass
        except KeyboardInterrupt:
            self.result = None
        curses.curs_set(0)
        return self.result

    def __enter__(self):
        return self

    def close(self):
        """Call the self.before_close hook and destroy the curses window."""
        if self.win is not None:
            self.before_close()
            del self.win
            self.win = None

    def __exit__(self, type_, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def event_p(self, key, name):
        """Wraps the event() method to call self.resize and optionally handle
        TAB keys."""
        if key == curses.KEY_RESIZE:
            self.resize()
            self.draw()
        elif Window.NO_TAB not in self.flags and isk_tab(key, name):
            self.tab()
            self.tabbed()
            self.draw()
        else:
            return self.event(key, name)
        return True

    def tab(self):
        """Move the cursor through self.tabcount and call self.tabbed."""
        self.current += 1
        if self.current >= self.tabcount:
            self.current = 0
        self.tabbed()

    def before_close(self):
        """Executed when going out of scope, just before destroying the
        curses window."""
        pass
    def tabbed(self):
        """Called when the tab key is pressed."""
        pass
    def draw(self):
        """The draw method."""
        pass
    def resize(self):
        """Resize hook.
        Called in the beginning and on terminal resize events.
        """
        pass
    def event(self, key, name):
        """Called when a key is pressed."""
        pass

    def center(self, height, width):
        """Move the window to the center given its current size."""
        # pylint: disable=invalid-name
        y, x = self.app.size
        y = (y - height) // 2
        x = (x - width)  // 2
        self.win.mvwin(y, x)

def yes_no(main, title, question):
    """Shows a 'Yes/No' dialog question."""
    with MsgBox(main, title, question) as dlg:
        return dlg.run() == MsgBox.YES_BUTTON

def no_yes(main, title, question):
    """Shows a 'Yes/No' dialog question. With 'No' being the frist and default
    button."""
    with MsgBox(main, title, question,
                buttons=[MsgBox.NO_BUTTON, MsgBox.YES_BUTTON]
               ) as dlg:
        return dlg.run() == MsgBox.YES_BUTTON

def message(main, title, text):
    """Shows a message box with an OK button."""
    with MsgBox(main, title, text, buttons=[MsgBox.OK_BUTTON]) as dlg:
        dlg.run()

def confirm(main, title, question):
    """Shows a confirmation request with OK and Cancel buttons."""
    with MsgBox(main, title, question,
                buttons=[MsgBox.OK_BUTTON, MsgBox.CANCEL_BUTTON]
               ) as dlg:
        return dlg.run() == MsgBox.OK_BUTTON

class MsgBox(Window):
    """A Message-Box Window subclass. Declares some buttons that can be shown
    along with a text message. Buttons default to 'Yes' and 'No'."""
    YES_BUTTON    = (0, L("Yes"))
    NO_BUTTON     = (1, L("No"))
    OK_BUTTON     = (2, L("OK"))
    CANCEL_BUTTON = (3, L("Cancel"))

    def __init__(self, app, title, question, buttons=[YES_BUTTON, NO_BUTTON]):
        # pylint: disable=dangerous-default-value
        Window.__init__(self, app)
        self.buttons   = buttons
        self.tabcount  = len(buttons)
        self.result    = buttons[0]

        textlines = question.splitlines()
        textwidth = 0
        for line in textlines:
            textwidth = max(textwidth, len(line))

        self.content = (title, textlines, textwidth)

        self.resize()

    def select(self, rel):
        """Move through the buttons and redraw."""
        self.current += rel
        while self.current < 0:
            self.current += self.tabcount
        while self.current >= self.tabcount:
            self.current -= self.tabcount
        self.draw()

    def event(self, key, name):
        if isk_enter(key, name):
            self.result = self.buttons[self.current]
            return False
        elif key == b'q':
            self.result = None
            return False
        elif isk_left(key, name):
            self.select(-1)
        elif isk_right(key, name):
            self.select(1)

        return True

    def resize(self):
        app = self.app
        width  = max(40, self.content[2] + 4)
        height = 6 + len(self.content[1])

        win_x = (app.size[1] - width)//2
        win_y = (app.size[0] - height)//2

        self.win.resize(height, width)
        self.win.mvwin (win_y, win_x)
        self.size = (height, width)

    def draw(self):
        fullh, fullw  = self.size

        width  = fullw - 2
        height = fullh - 2

        win = self.win
        rectangle(win, 0, 0, height, fullw-1)
        win.addstr(0, 3, '[%s]' % self.content[0])

        # pylint: disable=invalid-name
        y = 1
        for line in self.content[1]:
            win.hline (y, 1, ' ', width)
            win.addstr(y, 1, line)
            y += 1
        win.hline (y+0, 1, ' ', width)
        win.hline (y+1, 1, ' ', width)
        win.hline (y+2, 1, ' ', width)

        x = 1
        for i in range(self.tabcount):
            text = self.buttons[i][1]
            rectangle(win, y, x, y+2, x+len(text)+1)
            win.addstr(y+1, x+1, text, highlight_if(self.current == i))
            x += len(text)+3

        win.refresh()

class Dialog(Window):
    """
    A Dialog window contains a list of fields the user can write text into.
    """
    def __init__(self, app, title, fields):
        Window.__init__(self, app)
        self.title  = title
        self.fields = []
        self.fieldlen = 0
        for field in fields:
            self.fieldlen = max(self.fieldlen, len(field[0]))
            self.fields.append((field[0], field[1], str(field[2]), field[3]))
        self.fieldlen += 2
        self.tabcount = len(fields)+2

        # what we're currently typing to...
        self.cursor  = 0

        self.resize()
        self.tabbed()

    @staticmethod
    def is_valid_char(char, text, position, type_):
        """Check whether a character can be added at the given position of the
        given text, assuming the text represents a value of the specified
        type_, such as a byte-size or a label used for a partition."""
        if type_ == str:
            return char in string.printable

        if type_ == Label:
            return Label.allowed(char, text, position)

        if type_ == int:
            # 0x prefix allowed:
            if (len(text) > 1  and position == 1  and
                text[0] == '0' and (len(text) == 1 or text[1] != 'x') and
                char == 'x'):
                return True
            return char in string.digits

        if type_ == Size:
            return Size.allowed(char, text, position)

        return False

    def event(self, key, name):
        # pylint: disable=too-many-branches
        if isk_enter(key, name):
            if (self.current == len(self.fields)
                or Window.ENTER_ACCEPTS in self.flags):
                self.result = self.fields
                return False
            if self.current == len(self.fields)+1:
                self.result = None
                return False
            self.tab()
            self.draw()
            return True
        elif key == b'q':
            self.result = None
            return False
        elif self.current < len(self.fields):
            title, type_, value, limit = self.fields[self.current]
            char = chr(key)

            if self.is_valid_char(char, value, self.cursor, type_):
                # typing
                value = value[0:self.cursor] + char + value[self.cursor:]
                self.fields[self.current] = (title, type_, value, limit)
                self.cursor += 1

            elif isk_left(key, name):
                # move left
                self.cursor = max(0, self.cursor-1)
            elif isk_right(key, name):
                # move right
                self.cursor += 1
                self.cursor = min(self.cursor,
                                  len(self.fields[self.current][2]))
            elif isk_backspace(key, name):
                # backspace
                if self.cursor > 0:
                    value = value[0:self.cursor-1] + value[self.cursor:]
                    self.fields[self.current] = (title, type_, value, limit)
                    self.cursor -= 1

            elif isk_del(key, name):
                # delete
                if self.cursor < len(self.fields[self.current][2]):
                    value = value[0:self.cursor] + value[self.cursor+1:]
                    self.fields[self.current] = (title, type_, value, limit)

            elif isk_home(key, name):
                # home
                self.cursor = 0

            elif isk_end(key, name):
                # end
                self.cursor = len(self.fields[self.current][2])

            elif isk_del_to_front(key, name):
                # delete to the beginning of the line
                self.app.yank_add(value[:self.cursor])
                value = value[self.cursor:]
                self.fields[self.current] = (title, type_, value, limit)
                self.cursor = 0

            elif isk_del_to_end(key, name):
                # delete to the beginning of the line
                self.app.yank_add(value[self.cursor:])
                value = value[:self.cursor]
                self.fields[self.current] = (title, type_, value, limit)

            elif isk_yank(key, name):
                # paste from the yank buffer
                inner = self.app.yank_get()
                value = value[0:self.cursor] + inner + value[self.cursor:]
                self.cursor += len(inner)
                self.fields[self.current] = (title, type_, value, limit)

            self.draw()
        return True

    @staticmethod
    def check_field(label, type_, value, allowed):
        """Get the closest valid value for an input field.
        Returns the entire tuple for ease of use."""
        if allowed is None:
            return (label, type_, value, allowed)
        if type_ == str:
            # TODO: dropdown box behavior
            pass
        elif type_ == int or type_ == Size:
            min_, max_ = allowed
            value = str(max(min_, min(max_, int(value))))
        return (label, type_, value, allowed)

    def tabbed(self):
        if self.current >= len(self.fields):
            return
        field = self.fields[self.current]
        # pylint: disable=star-args
        field = self.check_field(*field)
        self.fields[self.current] = field
        self.cursor = len(field[2])

    def resize(self):
        app = self.app
        fullw  = 60  + 2
        fullh  = len(self.fields)*3 + 2

        fullh += 3 # buttons

        if fullw >= app.size[1]:
            fullw = app.size[1] - 4
        if fullh >= app.size[0]:
            fullh = app.size[0] - 4

        self.size = (fullh, fullw)

        win_x = (app.size[1] - fullw)//2
        win_y = (app.size[0] - fullh)//2

        self.win.resize(fullh+1, fullw+1)
        self.win.mvwin (win_y, win_x)


    def draw(self):
        height, width = self.size
        height -= 1
        width  -= 1

        win = self.win
        rectangle(win, 0, 0, height, width)
        win.addstr(0, 3, '[%s:]' % self.title)
        width -= 1

        # pylint: disable=invalid-name
        x = 1
        y = 1
        cursor = None
        for i in range(len(self.fields)):
            f = self.fields[i]
            title, _, value = f[0], f[1], f[2]
            win.hline (y+0, x, ' ', width)
            win.hline (y+1, x, ' ', width)
            win.hline (y+2, x, ' ', width)
            rectangle(win, y, x + self.fieldlen, y+2, x + width-1)
            win.addstr(y+1, x, '%s:' % title)
            win.addstr(y+1, x+1 + self.fieldlen, value)
            if self.current == i:
                cursor = (y+1, x+1 + self.fieldlen + len(value))
                cursor = (y+1, x+1 + self.fieldlen + self.cursor)
            y += 3

        win.hline(y+0, x, ' ', width)
        win.hline(y+1, x, ' ', width)
        win.hline(y+2, x, ' ', width)

        # OK button
        rectangle(win, y, x, y+2, x+9)
        attr = highlight_if(self.current == len(self.fields))
        win.addstr(y+1, x+1, '   OK   ', attr)

        x += 10
        # CANCEL button
        rectangle(win, y, x, y+2, x+9)
        attr = highlight_if(self.current == len(self.fields)+1)
        win.addstr(y+1, x+1, ' CANCEL ', attr)

        if cursor is None:
            curses.curs_set(0)
        else:
            curses.curs_set(1)
            # pylint: disable=star-args
            win.move(*cursor)
        win.refresh()

# Subwindow
class List(object):
    """List object subwindow. Handles scrolling/navigating/rendering a list."""
    def __init__(self, owner, at=(1,1), entries=[], name=None, userdata=None):
        self.owner     = owner
        self.win       = owner.win.derwin(at[0], at[1])

        self.pos       = 0
        self.scroll    = 0
        self.name      = name
        self.userdata  = userdata
        self.border    = True
        self.__size    = (0, 0)
        self.__entries = entries

    @property
    def entries(self):
        """get the current __entries"""
        return self.__entries

    @entries.setter
    def entries(self, value):
        """set the current __entries and update the current position in case
        the number of entries changed."""
        self.__entries = value
        self.pos = min(self.pos, len(value)-1)

    @property
    def size(self):
        """Get the current size."""
        return self.__size

    @size.setter
    def size(self, size):
        """Resize the window and underlying curses subwindow."""
        self.__size = size
        self.win.resize(size[0], size[1])

    def event(self, key, name):
        """Handle an event. Returns False if the event is not handled by this
        class."""
        # pylint: disable=too-many-branches
        maxpos = len(self.__entries)-1
        if isk_down(key, name):
            self.pos = min(self.pos+1, maxpos)

        elif isk_up(key, name):
            self.pos = max(self.pos-1, 0)

        elif isk_home(key, name):
            self.pos = 0

        elif isk_end(key, name):
            self.pos = maxpos

        elif isk_scrolldown(key, name):
            self.scroll = min(self.scroll+1, maxpos)

        elif isk_scrollup(key, name):
            self.scroll = max(self.scroll-1, 0)

        elif isk_pagedown(key, name):
            if self.pos != self.scroll + self.__size[0] - 4:
                self.pos = self.scroll + self.__size[0] - 4
            else:
                self.pos += self.__size[0]-4

            self.pos = min(maxpos, max(0, self.pos))

        elif isk_pageup(key, name):
            if self.pos != self.scroll:
                self.pos = self.scroll
            else:
                self.pos -= self.__size[0]-4
            self.pos = min(maxpos, max(0, self.pos))

        else:
            return False

        self.selection_changed()
        return True

    def selection_changed(self):
        """callback"""
        pass

    def entry(self):
        """shorthand to get the current entry"""
        return self.__entries[self.pos]

    def draw(self):
        """Draw the list including borders, scrollability markers, etc."""
        height, width = self.__size
        win = self.win

        win.clear()

        rectangle(win, 0, 0, height-2, width-1)
        if self.name is not None:
            win.addstr(0, 3, '[%s]' % self.name)

        # -2 for the rectangle borders
        height -= 3

        if self.pos < self.scroll:
            self.scroll = self.pos
        elif self.scroll < self.pos - height + 1:
            self.scroll =  self.pos - height + 1

        if self.scroll > 0:
            win.addstr(0,        width - 16, MORE_UP)
        if self.scroll + height < len(self.__entries):
            win.addstr(height+1, width - 16, MORE_DOWN)

        # pylint: disable=invalid-name
        x = 1
        y = 1
        eindex   = 0
        selected = self.pos - self.scroll
        for i in range(self.scroll, len(self.__entries)):
            if y > height:
                break
            ent, edata = self.__entries[i]
            # pylint: disable=star-args
            txt = ent.entry_text(self.owner, self.userdata, width, *edata)
            win.addstr(y, x, txt, highlight_if(eindex == selected))
            eindex += 1
            y      += 1
