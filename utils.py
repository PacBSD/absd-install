import curses
import string
from curses.textpad import Textbox, rectangle

import gettext
L = gettext.gettext

class Size:
    pass

def check_field(label, type_, value, allowed):
    if allowed is None:
        return (label, type_, value, allowed)
    if type_ == str:
        # TODO: dropdown box behavior
        pass
    elif type_ == int or type_ == Size:
        min_, max_ = allowed
        value = str(max(min_, min(max_, int(value))))
    return (label, type_, value, allowed)

def is_valid_char(ch, text, position, type_):
    if type_ == str:
        return True
    if type_ == int:
        # 0x prefix allowed:
        if len(text) > 1 and text[0] == '0' and position == 1 and ch == 'x':
            return True
        return ch in string.digits
    if type_ == Size:
        # 0x prefix allowed:
        if len(text) > 1 and text[0] == '0' and position == 1 and ch == 'x':
            return True
        if ch == ',' or ch == '.':
            # , is stripped and . is allowed
            return True
        if position == len(text) and ch in 'kMGT':
            return True
        return ch in string.digits
    return False

def translate_key(key):
    try:
        return curses.keyname(key)
    except ValueError:
        return key

# vim/emacs/lame key checks:
def isk_up(key, name):
    return key == curses.KEY_UP   or name == b'k' or name == b'^P'

def isk_down(key, name):
    return key == curses.KEY_DOWN or name == b'j' or name == b'^N'

def isk_left(key, name):
    return key == curses.KEY_LEFT or name == b'h' or name == b'^B'

def isk_right(key, name):
    return key == curses.KEY_RIGHT or name == b'l' or name == b'^F'

def isk_home(key, name):
    return key == curses.KEY_HOME or name == b'g' or name == b'^A'

# the emacs key binding here clashes with isk_scrolldown, make sure you test
# the more important one first...
def isk_end(key, name):
    return key == curses.KEY_END  or name == b'G' or name == b'^E'

def isk_pageup(key, name):
    return key == curses.KEY_PPAGE

def isk_pagedown(key, name):
    return key == curses.KEY_NPAGE

def isk_scrollup(key, name):
    return name == b'^Y'

def isk_scrolldown(key, name):
    return name == b'^E'

def isk_tab(key, name):
    return name == b'^I'

def isk_enter(key, name):
    return key == curses.KEY_ENTER

def isk_backspace(key, name):
    return key == curses.KEY_BACKSPACE or name == b'^H'

def isk_del(key, name):
    return key == curses.KEY_DC or name == b'^D'

class Window(object):
    def __init__(self, Main):
        self.Main     = Main
        self.result   = None
        self.current  = 0
        self.tabcount = 0
        self.win      = curses.newwin(5, 5)
        self.notab    = False

    def run(self):
        self.resize()
        self.draw()
        try:
            while self.event_p(*self.Main.get_key()):
                pass
        except KeyboardInterrupt:
            self.result = None
        return self.result

    def __enter__(self):
        return self

    def close(self):
        if self.win is not None:
            del self.win
            self.win = None

    def __exit__(self, type, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def event_p(self, key, name):
        if key == curses.KEY_RESIZE:
            self.Main.resize_event()
            self.resize()
            self.draw()
        elif not self.notab and isk_tab(key, name):
            self.current += 1
            if self.current >= self.tabcount:
                self.current = 0
            self.tabbed()
            self.draw()
        else:
            return self.event(key, name)
        return True

    def tabbed(self):
        pass
    def draw(self):
        pass
    def resize(self):
        pass

def YesNo(Main, title, question):
    with MsgBox(Main, title, question) as dlg:
        return dlg.run() == MsgBox.Yes

def NoYes(Main, title, question):
    with MsgBox(Main, title, question, buttons=[MsgBox.No, MsgBox.Yes]) as dlg:
        return dlg.run() == MsgBox.Yes

def Message(Main, title, text):
    with MsgBox(Main, title, text, buttons=[MsgBox.Ok]) as dlg:
        dlg.run()

def Confirm(Main, title, question):
    with MsgBox(Main, title, question,
                buttons=[MsgBox.Ok, MsgBox.Cancel]
               ) as dlg:
        return dlg.run() == MsgBox.Ok

class MsgBox(Window):
    Yes    = (0, L("Yes"))
    No     = (1, L("No"))
    Ok     = (2, L("OK"))
    Cancel = (3, L("Cancel"))

    def __init__(self, Main, title, question, buttons=[Yes, No]):
        Window.__init__(self, Main)
        self.title     = title
        self.textlines = question.splitlines()
        self.buttons   = buttons
        self.tabcount  = len(buttons)
        self.result    = buttons[0]
        self.textwidth = 0
        for line in self.textlines:
            self.textwidth = max(self.textwidth, len(line))
        self.resize()

    def select(self, rel):
        self.current += rel
        if self.current < 0:
            self.current = self.tabcount-1
        elif self.current >= self.tabcount:
            self.current = 0
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
        Main = self.Main
        self.fullw = max(40, self.textwidth + 4)
        self.fullh = 5 + len(self.textlines)

        self.width  = self.fullw - 2
        self.height = self.fullh - 2
        self.x = (Main.size[1] - self.fullw)//2
        self.y = (Main.size[0] - self.fullh)//2

        self.win.resize(self.fullh+1, self.fullw+1)
        self.win.mvwin (self.y,       self.x)

    def draw(self):
        Main   = self.Main
        fullw  = self.fullw
        fullh  = self.fullh
        width  = self.width
        height = self.height

        win = self.win
        rectangle(win, 0, 0, fullh-1, fullw-1)
        win.addstr(0, 3, '[%s:]' % self.title)

        y = 1
        for line in self.textlines:
            win.hline (y, 1, ' ', width)
            win.addstr(y, 1, line)
            y += 1
        win.hline (y+0, 1, ' ', width)
        win.hline (y+1, 1, ' ', width)
        win.hline (y+2, 1, ' ', width)

        x = 1
        for i in range(self.tabcount):
            attr = curses.A_REVERSE if self.current == i else curses.A_NORMAL
            text = self.buttons[i][1]
            rectangle(win, y, x, y+2, x+len(text)+1)
            win.addstr(y+1, x+1, text, attr)
            x += len(text)+3

        win.refresh()

class Dialog(Window):
    def __init__(self, Main, title, fields):
        Window.__init__(self, Main)
        self.title  = title
        self.fields = []
        self.fieldlen = 0
        for f in fields:
            self.fieldlen = max(self.fieldlen, len(f[0]))
            self.fields.append((f[0], f[1], str(f[2]), f[3]))
        self.fieldlen += 2
        self.tabcount = len(fields)+2

        # what we're currently typing to...
        self.cursor  = 0

        self.resize()

    def event(self, key, name):
        if isk_enter(key, name):
            if self.current == len(self.fields):
                self.result = self.fields
                return False
            if self.current == len(self.fields)+1:
                self.result = None
                return False
            self.tabbed()
            self.draw()
            return True
        elif key == b'q':
            self.result = None
            return False
        elif self.current < len(self.fields):
            title, type_, value, limit = self.fields[self.current]
            ch = chr(key)
            if isk_left(key, name):
                self.cursor = max(0, self.cursor-1)
            elif isk_right(key, name):
                self.cursor += 1
                self.cursor = min(self.cursor,
                                  len(self.fields[self.current][2]))
            elif isk_backspace(key, name):
                if self.cursor > 0:
                    value = value[0:self.cursor-1] + value[self.cursor:]
                    self.fields[self.current] = (title, type_, value, limit)
                    self.cursor -= 1
            elif isk_del(key, name):
                if self.cursor < len(self.fields[self.current][2]):
                    value = value[0:self.cursor] + value[self.cursor+1:]
                    self.fields[self.current] = (title, type_, value, limit)
            elif isk_home(key, name):
                self.cursor = 0
            elif isk_end(key, name):
                self.cursor = len(self.fields[self.current][2])
            elif (ch in string.printable and 
                  is_valid_char(ch, value, self.cursor, type_)
                 ):
                value = value[0:self.cursor] + ch + value[self.cursor:]
                self.fields[self.current] = (title, type_, value, limit)
                self.cursor += 1
            self.draw()
        return True

    def tabbed(self):
        if self.current >= len(self.fields):
            return
        f = self.fields[self.current]
        f = check_field(*f)
        self.fields[self.current] = f
        self.cursor = len(f[2])

    def resize(self):
        Main = self.Main
        self.fullw  = 60  + 2
        self.fullh  = len(self.fields)*3 + 2

        self.fullh += 3 # buttons

        if self.fullw >= Main.size[1]:
            self.fullw = Main.size[1] - 4
        if self.fullh >= Main.size[0]:
            self.fullh = Main.size[0] - 4

        self.width  = self.fullw - 2
        self.height = self.fullh - 2

        self.x = (Main.size[1] - self.fullw)//2
        self.y = (Main.size[0] - self.fullh)//2

        self.win.resize(self.fullh+1, self.fullw+1)
        self.win.mvwin (self.y,       self.x)


    def draw(self):
        Main   = self.Main
        fullw  = self.fullw
        fullh  = self.fullh
        width  = self.width
        height = self.height

        win = self.win
        rectangle(win, 0, 0, fullh-1, fullw-1)
        win.addstr(0, 3, '[%s:]' % self.title)

        x = 1
        y = 1
        cursor = None
        for i in range(len(self.fields)):
            f = self.fields[i]
            title, type_, value = f[0], f[1], f[2]
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

        if self.current == len(self.fields):
            attr = curses.A_REVERSE
        else:
            attr = curses.A_NORMAL

        # OK button
        rectangle(win, y, x, y+2, x+9)
        win.addstr(y+1, x+1, '   OK   ', attr)

        if self.current == len(self.fields)+1:
            attr = curses.A_REVERSE
        else:
            attr = curses.A_NORMAL

        x += 10
        # CANCEL button
        rectangle(win, y, x, y+2, x+9)
        win.addstr(y+1, x+1, ' CANCEL ', attr)

        if cursor is None:
            curses.curs_set(0)
        else:
            curses.curs_set(1)
            win.move(*cursor)
        win.refresh()
