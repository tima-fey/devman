from physics import update_speed

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
ROW_SPEED = 0
COLUMN_SPEED = 0

FILES_WITH_GARBAGE = {
    'duck': 'animations/duck.txt',
    'habble': 'animations/hubble.txt',
    'lamp': 'animations/lamp.txt',
    'trash_large': 'animations/trash_large.txt',
    'trash_small': 'animations/trash_small.txt',
    'trash_xl': 'animations/trash_xl.txt',
}
def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""
    global ROW_SPEED, COLUMN_SPEED
    rows_direction = columns_direction = 0
    space_pressed = False

    pressed_key_code = canvas.getch()

    if pressed_key_code == -1:
        # https://docs.python.org/3/library/curses.html#curses.window.getch
        # break
        return rows_direction, columns_direction, space_pressed

    if pressed_key_code == UP_KEY_CODE:
        ROW_SPEED, COLUMN_SPEED = update_speed(ROW_SPEED, COLUMN_SPEED, -1, 0)

    elif pressed_key_code == DOWN_KEY_CODE:
        ROW_SPEED, COLUMN_SPEED = update_speed(ROW_SPEED, COLUMN_SPEED, 1, 0)

    elif pressed_key_code == RIGHT_KEY_CODE:
        COLUMN_SPEED, COLUMN_SPEED = update_speed(ROW_SPEED, COLUMN_SPEED, 0, 1)

    elif pressed_key_code == LEFT_KEY_CODE:
        COLUMN_SPEED, COLUMN_SPEED = update_speed(ROW_SPEED, COLUMN_SPEED, 0, -1)

    elif pressed_key_code == SPACE_KEY_CODE:
        space_pressed = True
    
    return ROW_SPEED, COLUMN_SPEED, space_pressed


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas. Erase text instead of drawing if negative=True is specified."""
    
    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break
                
            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def get_frame_size(text):
    """Calculate size of multiline text fragment. Returns pair (rows number, colums number)"""
    
    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


def convert_seconds_to_iterations(seconds, timer):
    """ Multiply seconds on the timer and return result
    """
    return seconds * timer


def get_file(file_name):
    """Return content of the file
    """
    with open(file_name) as _file:
        content = _file.read()
    return content

def change_position(row, col, frame_row, frame_col, delta_row, delta_column, row_max, col_max):
    """Count new position acording to the button pushed by user

    Args:
    row - current row position
    col - current column position
    frame_row - row size of the frame
    frame_col - column size of the frame
    return (row, column) - new position
    """
    # delta_row, delta_column, _ = read_controls(canvas)
    # row_max, col_max = canvas.getmaxyx()
    new_position_row = row + delta_row
    new_position_col = col + delta_column
    if new_position_row + frame_row // 2 >= row_max - 6:
        new_position_row = row_max - 6 - frame_row // 2
    if new_position_row - frame_row // 2 <= -3:
        new_position_row = frame_row // 2 -3
    if new_position_col + frame_col // 2 >= col_max - 4:
        new_position_col = col_max - 4 - frame_col // 2
    if new_position_col - frame_col // 2 <= 0:
        new_position_col = frame_col // 2 
    return new_position_row, new_position_col

def get_garbage_animation():
    garbage_animation = {}
    for garbage_type, garbage_file in FILES_WITH_GARBAGE.items():
        with open(garbage_file) as _file:
            garbage_animation[garbage_type] = _file.read()
    return garbage_animation