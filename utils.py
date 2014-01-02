import curses
from curses.textpad import Textbox, rectangle

class Size:
    pass

class Window(object):
    def __init__(self, Main):
        self.Main     = Main
        self.result   = None
        self.current  = 0
        self.tabcount = 0

    def run(self):
        self.draw()
        try:
            while self.event_p(*self.Main.get_key()):
                pass
        except KeyboardInterrupt:
            pass
        curses.curs_set(0)
        return self.result

    def event_p(self, key, name):
        if name == b'q':
            return False
        elif key == curses.KEY_RESIZE:
            self.Main.resize_event(do_refresh=False)
            self.draw()
        elif name == b'^I':
            self.current += 1
            if self.current >= self.tabcount:
                self.current = 0
            self.draw()
        else:
            return self.event(key, name)
        return True

    def draw(self):
        pass


class YesNo(Window):
    def __init__(self, Main, title, question):
        Window.__init__(self, Main)
        self.title    = title
        self.question = question
        self.result   = False
        self.tabcount = 2

    def event(self, key, name):
        if key == curses.KEY_ENTER:
            self.result = (self.current == 0)
            return False
        return True

    def draw(self):
        Main = self.Main
        fullw = len(self.question) + 4
        fullh = 6

        width  = fullw - 1
        height = fullh - 2
        x = (Main.size[1] - fullw)//2
        y = (Main.size[0] - fullh)//2

        screen = Main.screen
        rectangle(screen, y, x, y+fullh-1, x+fullw)
        screen.addstr(y, x+3, '[%s:]' % self.title)
        x += 1
        y += 1
        screen.hline(y, x, ' ', width)
        screen.addstr(y, x, self.question)
        y += 1
        screen.hline(y+0, x, ' ', width)
        screen.hline(y+1, x, ' ', width)
        screen.hline(y+2, x, ' ', width)

        # OK button
        attr = curses.A_REVERSE if self.current == 0 else curses.A_NORMAL
        rectangle(screen, y, x, y+2, x+8)
        screen.addstr(y+1, x+1, '  YES  ', attr)

        attr = curses.A_REVERSE if self.current == 1 else curses.A_NORMAL
        x += 9
        # CANCEL button
        rectangle(screen, y, x, y+2, x+9)
        screen.addstr(y+1, x+1, '   NO   ', attr)
        Main.screen.refresh()

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

    def event(self, key, name):
        if key == curses.KEY_ENTER:
            if self.current == len(self.fields)+1:
                self.result = None
            else:
                self.result = self.fields
            return False
        return True

    def draw(self):
        Main = self.Main
        fullw  = 60  + 2
        fullh  = len(self.fields)*3 + 2

        fullh += 3 # buttons

        if fullw >= Main.size[1]:
            fullw = Main.size[1] - 4
        if fullh >= Main.size[0]:
            fullh = Main.size[0] - 4

        width  = fullw - 1
        height = fullh - 2

        x = (Main.size[1] - fullw)//2
        y = (Main.size[0] - fullh)//2

        screen = Main.screen

        rectangle(screen, y, x, y+fullh-1, x+fullw)
        screen.addstr(y, x+3, '[%s:]' % self.title)

        x += 1
        y += 1
        cursor = None
        for i in range(len(self.fields)):
            f = self.fields[i]
            title, type_, value = f[0], f[1], f[2]
            screen.hline (y+0, x, ' ', width)
            screen.hline (y+1, x, ' ', width)
            screen.hline (y+2, x, ' ', width)
            rectangle(screen, y, x + self.fieldlen, y+2, x + width-1)
            screen.addstr(y+1, x, '%s:' % title)
            screen.addstr(y+1, x+1 + self.fieldlen, value)
            if self.current == i:
                cursor = (y+1, x+1 + self.fieldlen + len(value))
            y += 3

        screen.hline(y+0, x, ' ', width)
        screen.hline(y+1, x, ' ', width)
        screen.hline(y+2, x, ' ', width)

        if self.current == len(self.fields):
            attr = curses.A_REVERSE
        else:
            attr = curses.A_NORMAL

        # OK button
        rectangle(screen, y, x, y+2, x+9)
        screen.addstr(y+1, x+1, '   OK   ', attr)

        if self.current == len(self.fields)+1:
            attr = curses.A_REVERSE
        else:
            attr = curses.A_NORMAL

        x += 10
        # CANCEL button
        rectangle(screen, y, x, y+2, x+9)
        screen.addstr(y+1, x+1, ' CANCEL ', attr)

        if cursor is None:
            curses.curs_set(0)
        else:
            curses.curs_set(1)
            screen.move(*cursor)
        curses.doupdate()
