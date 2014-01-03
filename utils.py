import curses
import string
from curses.textpad import Textbox, rectangle

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

class Window(object):
    def __init__(self, Main):
        self.Main     = Main
        self.result   = None
        self.current  = 0
        self.tabcount = 0
        self.win      = curses.newwin(5, 5)

    def run(self):
        self.resize()
        self.draw()
        try:
            while self.event_p(*self.Main.get_key()):
                pass
        except KeyboardInterrupt:
            pass
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
        if name == b'q':
            return False
        elif key == curses.KEY_RESIZE:
            self.Main.resize_event()
            self.resize()
            self.draw()
        elif name == b'^I':
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


class YesNo(Window):
    def __init__(self, Main, title, question):
        Window.__init__(self, Main)
        self.title    = title
        self.question = question
        self.result   = False
        self.tabcount = 2
        self.resize()

    def event(self, key, name):
        if key == curses.KEY_ENTER:
            self.result = (self.current == 0)
            return False
        return True

    def resize(self):
        Main = self.Main
        self.fullw = len(self.question) + 4
        self.fullh = 6

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
        win.hline (y, 1, ' ', width)
        win.addstr(y, 1, self.question)
        y += 1
        win.hline (y+0, 1, ' ', width)
        win.hline (y+1, 1, ' ', width)
        win.hline (y+2, 1, ' ', width)

        x = 1
        # OK button
        attr = curses.A_REVERSE if self.current == 0 else curses.A_NORMAL
        rectangle(win, y, x, y+2, x+8)
        win.addstr(y+1, x+1, '  YES  ', attr)

        attr = curses.A_REVERSE if self.current == 1 else curses.A_NORMAL
        x += 9
        # CANCEL button
        rectangle(win, y, x, y+2, x+9)
        win.addstr(y+1, x+1, '   NO   ', attr)
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
        if key == curses.KEY_ENTER:
            if self.current == len(self.fields):
                self.result = self.fields
                return False
            if self.current == len(self.fields)+1:
                self.result = None
                return False
            self.tabbed()
            self.draw()
            return True
        elif self.current < len(self.fields):
            title, type_, value, limit = self.fields[self.current]
            ch = chr(key)
            if   key == curses.KEY_LEFT  or name == b'^B':
                self.cursor = max(0, self.cursor-1)
            elif key == curses.KEY_RIGHT or name == b'^F':
                self.cursor += 1
                self.cursor = min(self.cursor,
                                  len(self.fields[self.current][2]))
            elif key == curses.KEY_BACKSPACE or name == b'^H':
                if self.cursor > 0:
                    value = value[0:self.cursor-1] + value[self.cursor:]
                    self.fields[self.current] = (title, type_, value, limit)
                    self.cursor -= 1
            elif key == curses.KEY_DC or name == b'^D':
                if self.cursor < len(self.fields[self.current][2]):
                    value = value[0:self.cursor] + value[self.cursor+1:]
                    self.fields[self.current] = (title, type_, value, limit)
            elif name == b'^A':
                self.cursor = 0
            elif name == b'^E':
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
