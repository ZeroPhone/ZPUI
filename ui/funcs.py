# -*- coding: utf-8 -*-

import string

from unidecode import unidecode

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "info")

printable_characters = set(string.printable)
replace_characters = {u"ö":u"o"}


def ellipsize(string, length, ellipsis="..."):
    if len(string) <= length:
        return string
    string = string[:(length-len(ellipsis))]
    return string+ellipsis

def format_for_screen(data, screen_width, break_words=False, linebreak=None):
    if '\r\n' in data: # anti-\r-aktion
        data = data.replace('\r\n', '\n')
    strings = data.split('\n')
    #Filter \n's
    data = ' \n '.join(strings) #Making sure linebreaks are surrounded by space characters so that when splitting by space you don't have to scan for linebreaks and just can compare
    words = data.split(' ')
    screen_data = []
    current_data = ""
    for word in words:
        #Five cases:
        if not word: #An empty line encountered somehow
            pass
        elif word == '\n': #A linebreak, need to indent them in a way
            screen_data.append(current_data)
            current_data = ""
            if linebreak is not None:
                screen_data.append(linebreak)
        elif len(word) <= screen_width-len(current_data): #Word fits on current line
            current_data += word+" "
        elif not break_words and len(word) <= screen_width:
            screen_data.append(current_data)
            current_data = word+" "
        else:
            space_on_current_line = screen_width-len(current_data)
            screen_data.append(current_data+word[:space_on_current_line])
            word = word[space_on_current_line:]
            current_line = ""
            while word:
                data = word[:screen_width]
                if len(data) == screen_width: #Full line taken
                    screen_data.append(data)
                else:
                    current_data = data+" "
                word = word[screen_width:]
    screen_data.append(current_data)
    return screen_data

ffs = format_for_screen

def format_values_into_text_grid(values, o):
    # Formats values in a grid that uses as much of a screen space as possible
    # going like this:
    # 1 3  5 11  13
    # 2 4 10 12 101
    vals = [str(el) for el in values]
    x_off = 0
    col_i = 0
    cols = [] # columns of text
    for i, val in enumerate(vals):
        div, mod = divmod(i, o.rows)
        if len(cols) <= div:
            cols.append([])
        if len(cols[col_i]) < o.rows:
            cols[col_i].append(val)
        else:
            row = [len(x) for x in cols[col_i]]
            prev_row_width = max(row) if row else 0
            x_off += prev_row_width+1
            if x_off > o.cols:
                break
            col_i += 1
            cols[col_i].append(val)
    # filtering empty cols
    cols = list(filter(None, cols))
    # padding string values
    for a, col in enumerate(cols):
        max_len = max([len(x) for x in col])
        for b, el in enumerate(col):
            if len(el) < max_len:
                cols[a][b] = " "*(max_len-len(el))+el
    # creating the actual strings to be sent to display_data
    screen_data = []
    for i in range(o.rows):
        vals = [col[i] for col in cols if len(col)>i]
        screen_data.append(" ".join(vals))
    return screen_data

fvitg = format_values_into_text_grid

def add_character_replacement(character, replacement):
    """
    In case a Unicode character isn't replaced in the way you want it replaced,
    use this function to add a special case.
    """
    logger.info(u"Adding char replacement: {} for {}".format(character, replacement))
    if character in replace_characters:
        logger.warning(u"Character {} already set! (to {} )".format(character, replace_characters[character]))
    replace_characters[character] = replacement

acr = add_character_replacement

def replace_filter_ascii(text, replace_characters=replace_characters):
    """
    Replaces non-ASCII characters with their ASCII equivalents if available,
    removes them otherwise. You can add new replacement characters using the
    ``add_character_replacement`` function. The output of this function is ASCII
    printable characters.

    This function is mostly useful because the default PIL font doesn't have many Unicode
    characters (in fact, it's doubtful it has any). So, if you're going to display
    strings with Unicode characters, you'll want to use this function to filter your
    text before displaying.
    """
    try:
        if isinstance(text, str) and not isinstance(text, unicode):
            text = text.decode('utf-8')
    except NameError:
        if isinstance(text, bytes):
            text = text.decode('utf-8')
    # First, developer-added exceptions
    for character, replacement in replace_characters.items():
        if character in text:
            text = text.replace(character, replacement)
    # Then, use the unidecode() function
    text = unidecode(text)
    # Filter all non-printable characters left
    text = "".join(list(filter(lambda x: x in printable_characters, text)))
    return text

rfa = replace_filter_ascii
