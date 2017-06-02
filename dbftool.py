# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dbftool - DBF console Viewer/Editor for Linux.

Command format:
    export COLUMNS LINES; python dbftool.py [options] dbf_file_name.dbf
    
Options:
        --help | -h | -?    View help
        --version | -v      View version
        --log | -l          On logging mode
                
        --encoding=         DBF codepage.
"""

import sys
import datetime
import logging
import getopt
import os
import os.path
import traceback

# try:
#     import dbfpy.dbf
# except ImportError:
#     print(u'Import error <dbfpy>')

try:
    import urwid
except ImportError:
    print(u'Import error <urwid>')
    print(u'Use <sudo apt-get install python-urwid>')


# Version
__version__ = (0, 0, 0, 2)

DEFAULT_ENCODING = 'utf-8'
DBF_ENCODING = 'cp866'

PROFILE_DIR = os.path.join(os.environ.get('HOME', os.path.join(os.path.dirname(__file__), 'log')), '.icdbftool')

# Полное имя DBF файла
DBF_FILENAME = None

# Количество записей DBF файла
DBF_RECORD_COUNT = 0

# RUS: Функции поддержки режима журналирования
# ENG: Logging mode functions

LOG_FILENAME = os.path.join(PROFILE_DIR, 'dbftool_%s.log' % datetime.date.today().isoformat())
LOG_MODE = True

# Разделитель полей в строке
FIELD_SEPARATOR = u'|'
COLUMN_SEPARATOR = u'│'


def log_init(sLogFileName=None, reNew=True):
    """
    RUS:
        Инициализация режима журналирования.
    ENG:
        Init logging mode.
    """
    if not LOG_MODE:
        return
    
    if sLogFileName is None:
        sLogFileName = LOG_FILENAME
        
    # Создать папку логов если она отсутствует
    log_dirname = os.path.normpath(os.path.dirname(sLogFileName))
    if not os.path.exists(log_dirname):
        try:
            os.makedirs(log_dirname)
        except:
            print(u'Error create dir <%s>' % log_dirname)
    if reNew and os.path.exists(sLogFileName):
        try:
            os.remove(sLogFileName)
        except:
            print(u'Error remove <%s>' % sLogFileName)
        
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename=sLogFileName,
                        filemode='a')


def log_debug(sMsg, bForceLog=False):
    """
    RUS: Запись отладочного сообщения в журнал.
    ENG: Write DEBUG message in log.
    @param sMsg: RUS: Текст сообщения. ENG: Message text.
    @param bForceLog: RUS: Принудительная запись в журнал. ENG: Force logging.
    """
    if LOG_MODE or bForceLog:
        logging.debug(sMsg)


def log_info(sMsg, bForceLog=False):
    """
    RUS:
    ENG: Write INFO message in log.
    @param sMsg: ENG: Message text.
    @param bForceLog: ENG: Force logging.
    """
    if LOG_MODE or bForceLog:
        logging.info(sMsg)    


def log_error(sMsg, bForceLog=False):
    """
    ENG: Write ERROR message in log.
    @param sMsg: ENG: Message text.
    @param bForceLog: ENG: Force logging.
    """
    if LOG_MODE or bForceLog:
        logging.error(sMsg)    


def log_warning(sMsg, bForceLog=False):
    """
    ENG: Write WARNING message in log.
    @param sMsg: ENG: Message text.
    @param bForceLog: ENG: Force logging.
    """
    if LOG_MODE or bForceLog:
        logging.warning(sMsg)    


def log_fatal(sMsg, bForceLog=False):
    """
    ENG: Write CRITICAL message in log.
    @param sMsg: ENG: Message text.
    @param bForceLog: ENG: Force logging.
    """
    trace_txt = traceback.format_exc()

    try:
        msg = sMsg+u'\n'+trace_txt
    except UnicodeDecodeError:
        if not isinstance(sMsg, unicode):
            sMsg = unicode(sMsg, DEFAULT_ENCODING)
        if not isinstance(trace_txt, unicode):
            trace_txt = unicode(trace_txt, DEFAULT_ENCODING)
        msg = sMsg+u'\n'+trace_txt

    if LOG_MODE or bForceLog:
            logging.fatal(msg)


def get_linux_terminal_size():
    """
    Определить размер терминала Linux в знакопозициях.
    @return: Кортеж: Высота терминала Linux в знакопозициях, ширина терминала Linux в знакопозициях.
    """
    try:
        rows, columns = os.popen('stty size', 'r').read().split()
        return int(rows), int(columns)
    except:
        log_fatal(u'Ошибка определения размера терминала')
    # Значение по умолчанию
    return 24, 80


# ENG: DBF table functions
SCREEN_HEIGHT, SCREEN_WIDTH = get_linux_terminal_size()

FIELD_SCREEN_START = 0                  # Поле с которого начинается отображение
FIELD_SCREEN_STOP = None                # Поле которым оканчвается отображение
REC_SCREEN_START = 0                    # Запись с которого начинается отображение
REC_SCREEN_STOP = SCREEN_HEIGHT - 2     # Запись которым заканчивается отображение

MAX_FIELD_SCREEN_START = None
CURSOR_SCREEN = 0               # Курсор строки. Индекс записи


def calc_field_screen(field_defs=None):
    """
    RUS: Расчет диапазона отображаемых на экране полей.
    """
    global FIELD_SCREEN_START
    global FIELD_SCREEN_STOP
    global SCREEN_WIDTH
    global MAX_FIELD_SCREEN_START
    
    if field_defs is None:
        field_defs = read_dbf_table_fielddefs()

    if FIELD_SCREEN_START <= MAX_FIELD_SCREEN_START:
        length = 0
        fields = list(field_defs)[FIELD_SCREEN_START:]
        end = True
        for i, field in enumerate(fields):
            length += field['length']+field['decimal']+1 if field['decimal'] else field['length']
            if length > SCREEN_WIDTH:
                FIELD_SCREEN_STOP = min(FIELD_SCREEN_START+i, len(field_defs)-1)
                FIELD_SCREEN_START = min(FIELD_SCREEN_STOP-i, MAX_FIELD_SCREEN_START)
                # log_debug(u'Field screen [%s : %s] - %s : %s' % (FIELD_SCREEN_START, FIELD_SCREEN_STOP, i, len(field_defs)))
                end = False
                break
        if end:
            FIELD_SCREEN_STOP = len(field_defs) - 1
            
    else:
        FIELD_SCREEN_START = MAX_FIELD_SCREEN_START
        FIELD_SCREEN_STOP = len(field_defs) - 1


def calc_max_field_screen_start(field_defs=None):
    """
    """
    if field_defs is None:
        field_defs = read_dbf_table_fielddefs()

    length = 0
    fields = list(field_defs)
    # fields.reverse()
    result = 0
       
    for i in range(len(fields) - 1, -1, -1):
        field = fields[i]
        length += field['length']+field['decimal']+1 if field['decimal'] else field['length']
        if length >= SCREEN_WIDTH:
            result = i
            break
    return result


def read_dbf_table_fielddefs(dbf_filename=None):
    """
    RUS: Чтение определение полей DBF таблицы.
    @return: Список словарей описаний полей DBF таблицы.
    """
    if dbf_filename is None:
        global DBF_FILENAME
        dbf_filename = DBF_FILENAME

    lines = get_nixdbf_cmd(u'--dbf="%s"' % dbf_filename, u'--cmd=FIELDS')
    fields = [line.strip().split(FIELD_SEPARATOR) for line in lines]
    field_defs = [dict(name=field[0], typ=field[1],
                       length=int(field[2]), decimal=int(field[3])) for field in fields]
    return field_defs
    
    
def read_dbf_table_fields(dbf_filename=None):
    """
    RUS: Чтение списка определения полей DBF таблицы.
    ENG: Read DBF table field defenition.
    @param dbf_filename: RUS: Полное наименование DBF файла таблицы. ENG: File name of DBF table.
    """
    fields = read_dbf_table_fielddefs(dbf_filename)

    global FIELD_SCREEN_START
    global FIELD_SCREEN_STOP
    # log_debug(u'\tField screen [%s : %s]' % (FIELD_SCREEN_START, FIELD_SCREEN_STOP))
    return tuple([field for field in fields[FIELD_SCREEN_START:FIELD_SCREEN_STOP]])


def read_dbf_table_record_count(dbf_filename=None):
    """
    RUS: Определение количества записей DBF таблицы.
    @return: Количество записей DBF таблицы.
    """
    if dbf_filename is None:
        global DBF_FILENAME
        dbf_filename = DBF_FILENAME

    lines = get_nixdbf_cmd(u'--dbf="%s"' % dbf_filename, u'--cmd=LENGTH')
    rec_count = [int(line) for line in lines][0] if lines else 0
    return rec_count


def get_nixdbf_cmd(*args):
    """
    Получить результат выполнения коммандной строки выхова утилиты NixDBF.
    @param args: Параметры коммандной строки NixDBF.
    @return: Список строк, выдаваемых утилитой NixDBF.
    """
    cmd_args_txt = u' '.join([unicode(arg if isinstance(arg, str) else str(arg),
                                      DEFAULT_ENCODING) if not isinstance(arg,
                                                                          unicode) else arg for arg in args])
    cmd = u'nixdbf %s' % cmd_args_txt
    try:
        # log_debug(u'Запуск комманды <%s>' % cmd)
        in_stream, out_stream, err_stream = os.popen3(cmd)
        return [unicode(line, DEFAULT_ENCODING) for line in out_stream]
    except:
        log_fatal(u'Error execute command <%s>' % cmd)
    return list()


def read_dbf_table_records(dbf_filename=None, dbf_encoding=None):
    """
    RUS: Чтение записей DBF таблицы.
    ENG: Read DBF table records.
    @param dbf_filename: RUS: Полное наименование DBF файла таблицы. ENG: File name of DBF table.
    """
    global DBF_ENCODING
    global FIELD_SCREEN_START
    global FIELD_SCREEN_STOP
    global REC_SCREEN_START
    global REC_SCREEN_STOP

    if dbf_encoding is None:
        dbf_encoding = DBF_ENCODING

    if dbf_filename is None:
        global DBF_FILENAME
        dbf_filename = DBF_FILENAME

    lines = get_nixdbf_cmd(u'--dbf="%s"' % dbf_filename,
                           u'--cmd=SELECT',
                           u'--src_codepage="%s"' % dbf_encoding.upper(),
                           u'--dst_codepage="%s"' % DEFAULT_ENCODING.upper(),
                           u'--start_rec=%d' % REC_SCREEN_START,
                           u'--limit=%d' % (REC_SCREEN_STOP - REC_SCREEN_START))
    records = [line.strip().split(FIELD_SEPARATOR) for line in lines]

    result = list()
    for record in records:
        norm_record = tuple([unicode(field, DEFAULT_ENCODING) if not isinstance(field, unicode) else field for field in list(record)[FIELD_SCREEN_START:FIELD_SCREEN_STOP]])
        result.append(norm_record)
    return result


def show_cursor(frame, cursor_idx=-1):
    """
    Отобразить курсор.
    @param cursor_idx: Индекс строки записи, на которой находиться курсор. 
    """
    global CURSOR_SCREEN
    global REC_SCREEN_START
    global REC_SCREEN_STOP
    global SCREEN_HEIGHT
    global DBF_RECORD_COUNT
    global FOOTER_TEXT

    if cursor_idx < 0:
        cursor_idx = CURSOR_SCREEN

    # Контроль индекса
    if cursor_idx < 0:
        REC_SCREEN_START -= 1
        if REC_SCREEN_START < 0:
            REC_SCREEN_START = 0
        else:
            REC_SCREEN_STOP -= 1
        cursor_idx = 0
    elif cursor_idx >= (REC_SCREEN_STOP - REC_SCREEN_START):
        REC_SCREEN_START += 1
        if REC_SCREEN_START >= DBF_RECORD_COUNT:
            REC_SCREEN_START = DBF_RECORD_COUNT - (SCREEN_HEIGHT - 2)
        else:
            REC_SCREEN_STOP += 1
        cursor_idx = SCREEN_HEIGHT - 3
        # log_debug(u'Переход на следующий кадр %d [%d : %d]' % (cursor_idx, REC_SCREEN_START, REC_SCREEN_STOP))

    list_box = frame.get_body().base_widget
    list_box.set_focus(cursor_idx)
    CURSOR_SCREEN = cursor_idx

    log_debug(u'Cursor %d screen start %d' % (CURSOR_SCREEN, REC_SCREEN_START))

    # Отобразить номер строки на панели
    FOOTER_TEXT[1] = ('footer', u' : %d / %d' % (REC_SCREEN_START+CURSOR_SCREEN+1, DBF_RECORD_COUNT))


EXIT_FLAG = False


def on_key_event(key):
    """
    RUS: Обработчик событий клавиатуры.
    """
    global EXIT_FLAG
    global FIELD_SCREEN_START
    global CURSOR_SCREEN

    if key == 'esc':
        EXIT_FLAG = True
        raise urwid.ExitMainLoop()
    elif key == 'left':
        FIELD_SCREEN_START = max(0, FIELD_SCREEN_START-1)
        raise urwid.ExitMainLoop()
    elif key == 'right':
        FIELD_SCREEN_START += 1
        raise urwid.ExitMainLoop()
    elif key == 'up':
        # CURSOR_SCREEN = max(0, CURSOR_SCREEN-1)
        CURSOR_SCREEN -= 1
        raise urwid.ExitMainLoop()
    elif key == 'down':
        CURSOR_SCREEN += 1
        raise urwid.ExitMainLoop()


FOOTER_TEXT = [('footer', ''), '    ',
               ('footer', ''), '    ',
               ('num', '1'), ' ',
               ('key', 'ESC - Exit'), ' ',
               ]
    
PALLETE = [('body', 'black', 'yellow', 'standout'),
           ('border', 'yellow', 'dark blue'),
           ('footer', 'black', 'dark cyan'),
           ('shadow', 'white', 'black'),
           ('selectable', 'white', 'dark blue'),
           ('focus', 'black', 'dark cyan', 'bold'),
           ('focustext', 'yellow', 'dark blue'),
           ('num', 'white', 'black'),
           ('key', 'black', 'dark cyan'),
           ('fixed', 'black', 'dark cyan'),
           ]


def browse_dbf_table(dbf_filename=None):
    """
    Открыть браузер DBF таблицы.
    @param dbf_filename: RUS: Полное наименование DBF файла таблицы. ENG: File name of DBF table.
    """
    global SCREEN_WIDTH
    global SCREEN_HEIGHT
    global DBF_FILENAME
    global FOOTER_TEXT
    global DBF_ENCODING
    global MAX_FIELD_SCREEN_START
    global FIELD_SCREEN_START
    global DBF_RECORD_COUNT

    if dbf_filename:
        dbf_filename = os.path.normpath(dbf_filename)
        if not os.path.exists(dbf_filename):
            log_warning(u'DBF file not exists <%s>' % dbf_filename)
            return
        DBF_FILENAME = dbf_filename
    else:
        dbf_filename = DBF_FILENAME

    FOOTER_TEXT[0] = ('footer', os.path.basename(dbf_filename))
    log_debug(u'DBF file name <%s>' % dbf_filename)

    DBF_RECORD_COUNT = read_dbf_table_record_count(dbf_filename)
    FOOTER_TEXT[1] = ('footer', u' : 1 / %d' % DBF_RECORD_COUNT)
    MAX_FIELD_SCREEN_START = calc_max_field_screen_start()

    while not EXIT_FLAG:
        calc_field_screen()
        fields = read_dbf_table_fields(dbf_filename)
        # log_debug(u'%d Fields <%s>' % (len(fields), str(fields)))
        records = read_dbf_table_records(dbf_filename)

        header = urwid.Columns([('fixed', field['length']+field['decimal']+2,
                                 urwid.Text(field['name'][:field['length']+field['decimal']+1])) for field in fields])

        contents = list()
        for i_rec, record in enumerate(records):
            # log_debug(u'%d record %s' % (len(record), str(record)))
            col_content = [('fixed', fields[i]['length']+fields[i]['decimal']+2,
                            urwid.Text(item + COLUMN_SEPARATOR)) for i, item in enumerate(record)]
            if col_content:
                columns = urwid.Columns(col_content)
            else:
                # Если нет колонок для добавления в список то все равно создать фиктивную
                columns = urwid.Columns([('fixed', SCREEN_WIDTH, urwid.Text(u''))])
            contents.append(urwid.AttrMap(columns, 'selectable', 'focus'))

        interrior = urwid.ListBox(urwid.SimpleFocusListWalker(contents))

        view = urwid.Frame(urwid.AttrWrap(interrior, 'selectable'),
                           header=urwid.AttrWrap(header, 'border'),
                           footer=urwid.AttrWrap(urwid.Text(FOOTER_TEXT), 'footer'))

        show_cursor(view)
        loop = urwid.MainLoop(view, PALLETE, unhandled_input=on_key_event)
        loop.run()


def main(*argv):
    """
    RUS: Главная запускаемая функция.
    ENG: Main function.
    @param argv: RUS: Параметры коммандной строки. ENG: Command parameters.
    """
    log_init()
    log_debug(u'Terminal [%d x %d]' % (SCREEN_WIDTH, SCREEN_HEIGHT))

    if not argv:
        print(__doc__)
        sys.exit(0)

    argv = [arg for arg in argv if '.dbf' not in arg or '.DBF' not in arg]
    dbf_file_find = [arg for arg in argv if '.dbf' in arg or '.DBF' in arg]
    dbf_filename = dbf_file_find[0] if dbf_file_find else None

    try:
        options, args = getopt.getopt(argv, 'h?vl',
                                      ['help', 'version', 'log'])
    except getopt.error, msg:
        print(u'Paremeters error. For help use --help option.')
        sys.exit(2)

    for option, arg in options:
        if option in ('-h', '--help', '-?'):
            print(__doc__)
            sys.exit(0)
        elif option in ('-v', '--version'):
            version = '.'.join([str(sign) for sign in __version__])
            print(u'icDBFTool. version: %s' % version)
            sys.exit(0)
        elif option in ('--log', '-l'):
            global LOG_MODE
            LOG_MODE = True
            log_init()
        elif option in ('--encoding',):
            global DBF_ENCODING
            DBF_ENCODING = arg.upper()

    browse_dbf_table(dbf_filename)

   
if __name__ == '__main__':
    main(*sys.argv[1:])
