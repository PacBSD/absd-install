#!/usr/bin/python3

import part
import utils
import i_parted
from geom import geom

import os
import curses
import atexit
from curses.textpad import Textbox, rectangle

###############################################################################

Main = lambda: None

###############################################################################

def print_tables(tables):
    # now print the layout
    for t in tables:
        print('%s (%s) [%u, %u]' % (t.name, t.scheme, t.first, t.last))
        for p in t.partitions:
            print('\t %s (%s) [%u, %u]' % (p.name, p.partype, p.start, p.end))

def main():
    Main.screen = curses.initscr()
    curses.start_color()
    atexit.register(gui_shutdown)
    curses.savetty()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)

    Main.screen.keypad(True)
    Main.size = Main.screen.getmaxyx()

    # fstab entries...
    Main.fstab       = []

    # callbacks
    Main.draw_gui      = draw_gui
    Main.resize_event  = resize_event
    Main.translate_key = translate_key
    Main.get_key       = get_key

    # which geoms are currently open in the tree view
    Main.tables_open   = []
    Main.tables_scroll = 0
    Main.tables_pos    = 0
    Main.tables_count  = 0
    Main.status_msg    = "Create/Select partitions to install on."
    Main.tables_sel    = None

    show_gui()

    gui_shutdown()
    atexit.unregister(gui_shutdown)
    part.info()

def gui_shutdown():
    curses.resetty()
    curses.endwin()
    os.system('stty sane')

def resize_event(do_refresh=True):
    Main.size = Main.screen.getmaxyx()
    draw_gui(do_refresh=do_refresh)

class EntryType:
    Table     = 0
    Partition = 1
    Free      = 2

def table_contents(tables, do_open = False):
    entries = []
    longest = 0
    for t in tables:
        if do_open:
            if len(entries) == Main.tables_pos:
                if t.name in Main.tables_open:
                    Main.tables_open.remove(t.name)
                else:
                    Main.tables_open.append(t.name)

        longest = max(longest, len(t.name))
        if t.name not in Main.tables_open:
            entries.append((EntryType.Table, t, False))
            continue

        # This entry is 'open':
        entries.append((EntryType.Table, t, True))

        last = None
        for i in range(len(t.partitions)):
            p = t.partitions[i]
            last = p
            if i == 0 and p.start > t.first:
                entries.append((EntryType.Free, t,
                                t.first,
                                p.start - t.first
                               ))
            if i > 0:
                prev = t.partitions[i-1]
                if prev.end+1 != p.start:
                    entries.append((EntryType.Free, t,
                                    prev.end+1,
                                    p.start - prev.end
                                   ))
            longest = max(longest, len(p.name))
            entries.append((EntryType.Partition, t, p))
        if last is None:
            last = t.first
        else:
            last = last.end

        if last < t.last:
            entries.append((EntryType.Free, t,
                            last,
                            t.last - last
                           ))

    parts = []
    for e in entries:
        if e[0] == EntryType.Table:
            table   = e[1]
            opened  = '-' if e[2] else '+'
            padding = ' ' * (longest - len(table.name))

            txt = '%s %s%s% 6s [%s]' % (opened,
                                        table.name,
                                        padding,
                                        table.scheme,
                                        part.bytes2str(table.size))
        elif e[0] == EntryType.Free:
            t = e[1]
            txt = '    free: (%s)' % (part.bytes2str(e[3] * t.sectorsize))
        elif e[0] == EntryType.Partition:
            table   = e[1]
            p       = e[2]
            padding = ' ' * (4 + longest - len(p.name))

            txt = ' -> %s%s %- 14s (%s)' % (p.name, padding, p.partype,
                                            part.bytes2str(p.bytes_)
                                           )
            if p.label is not None:
                txt += " [%s]" % p.label
        else:
            txt = '<error>'
        parts.append((txt, e))

    return parts

def draw_gui(do_refresh=True, do_open=False):
    Main.screen.clear()
    try:
        Main.screen.hline (0, 0, ' ', Main.size[1])
        if Main.status_msg is not None:
            Main.screen.addstr(0, 0, Main.status_msg)
    except curses.error:
        pass

    # to be always up to date we (re)load the geometry here
    Main.tables = part.load()

    # Layout window: Layout + rectangle + contents = 3 + contents
    layout_height = 3 + len(Main.fstab)
    rectangle(Main.screen, Main.size[0] - layout_height, 1,
              Main.size[0]-2, Main.size[1]-2)
    Main.screen.addstr(Main.size[0] - layout_height - 1, 1,
                       "Install Layout (/etc/fstab entries):")

    partitions = table_contents(Main.tables, do_open)
    Main.tables_count = len(partitions)

    max_height = Main.size[0] - layout_height - 3
    Main.tables_height = max_height - 3

    if Main.tables_pos < Main.tables_scroll:
        Main.tables_scroll = Main.tables_pos
    elif Main.tables_pos - Main.tables_scroll > Main.tables_height:
        Main.tables_scroll = Main.tables_pos - Main.tables_height

    scroll = Main.tables_scroll
    y = 1
    selected_y = Main.tables_pos - scroll + 2

    rectangle(Main.screen, 1, 1, max_height, Main.size[1]-2)
    if Main.tables_height < len(partitions):
        if scroll > 0:
            Main.screen.addstr(1, Main.size[1]-2-16, ' [ ^^^ more ] ')
        if len(partitions)-scroll-1 > Main.tables_height:
            Main.screen.addstr(max_height, Main.size[1]-2-16, ' [ vvv more ] ')

    for (p,entry) in partitions:
        if scroll > 0:
            scroll -= 1
            continue
        y += 1
        if y == max_height:
            break
        Main.screen.hline (y, 3, ' ', Main.size[1]-5)
        if y == selected_y:
            attr = curses.A_REVERSE
            Main.tables_sel = (p,entry)
        else:
            attr = curses.A_NORMAL
        Main.screen.addstr(y, 3, p, attr)

    if do_refresh:
        Main.screen.refresh()

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

def translate_key(key):
    try:
        return curses.keyname(key)
    except ValueError:
        return key

def get_key():
    key  = Main.screen.getch()
    name = translate_key(key)
    if key == 0x7f:
        key = curses.KEY_BACKSPACE
    elif key == 0x0a:
        key = curses.KEY_ENTER
    return (key, name)

def event_loop():
    draw_gui()
    while True:
        key, name = get_key()

        if name == b'q':
            break
        elif key == curses.KEY_DOWN or name == b'j' or name == b'^N':
            Main.tables_pos = min(Main.tables_pos+1, Main.tables_count-1)
            draw_gui()
        elif key == curses.KEY_UP   or name == b'k' or name == b'^P':
            Main.tables_pos = max(Main.tables_pos-1, 0)
            draw_gui()
        elif key == curses.KEY_HOME or name == b'g':
            Main.tables_pos = 0
            draw_gui()
        elif key == curses.KEY_END  or name == b'G':
            Main.tables_pos = Main.tables_count-1
            draw_gui()
        elif name == b' ':
            draw_gui(do_open=True)
        elif key == curses.KEY_ENTER:
            partition_action()
            draw_gui()
        elif key == curses.KEY_RESIZE:
            resize_event()
        else: # debugging
            Main.status_msg = "Key event! '%s' %x %x" % (name,
                                                         key&255,
                                                         key)
            draw_gui()

def show_gui():
    try:
        #event_loop()
        Main.screen.refresh()
        with i_parted.Parted(Main) as parted:
            parted.run()
    except KeyboardInterrupt:
        pass
    except Exception as inst:
        try:
            gui_shutdown()
            atexit.unregister(gui_shutdown)
        except:
            pass
        raise inst

if __name__ == '__main__':
    main()
