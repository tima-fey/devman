import sys
import random
import curses
import asyncio

from tools import draw_frame, read_controls,\
    change_position, get_frame_size, get_garbage_animation, get_garbage_delay_tics,\
    PHRASES
from obstacles import Obstacle
from explosion import explode

with open('animations/spaceship_frame_1.txt') as _file:
    SPACESHIP_FRAME1 = _file.read()
with open('animations/spaceship_frame_2.txt') as _file:
    SPACESHIP_FRAME2 = _file.read()
current_spaceship_frame = SPACESHIP_FRAME1
old_spaceship_frame = SPACESHIP_FRAME2
spaceship_speed_row, spaceship_speed_col = 0, 0
spaceship_position_row = 0
spaceship_position_col = 0
active_obstacles = {}
with open('animations/gameover.txt') as _file:
    GAMEOVER = _file.read()
year = 1957
tasks = list()

try:
    SPEED = int(sys.argv[1])
except (IndexError, ValueError):
    SPEED = 5

class EventLoopCommand():

    def __await__(self):
        return (yield self)

class Sleep(EventLoopCommand):
    def __init__(self, seconds):
        self.seconds = seconds

async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0.1)
    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0.1)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        for key in list(active_obstacles.keys()):
#cant remove list(), or I get RuntimeError: dictionary changed size during iteration
            if active_obstacles[key].has_collision(round(row), round(column)):
                canvas.addstr(round(row), round(column), ' ')
                active_obstacles.pop(key)
                return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0.1)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed

async def blink(canvas, row, column, symbol='*'):
    """Display blinking stairs
    """
    await asyncio.sleep(random.randint(0, 200)/100)
    actions = ((curses.A_DIM, 2), (curses.A_NORMAL, 0.3),\
        (curses.A_BOLD, 0.5), (curses.A_NORMAL, 0.3))
    while True:
        for (action, sleep_time) in actions:
            canvas.addstr(row, column, symbol, action)
            await asyncio.sleep(sleep_time)

async def run_spaceship(canvas):
    global spaceship_position_row, spaceship_position_col
    field_size_row, field_size_col = canvas.getmaxyx()
    spaceship_size_row, spaceship_size_col = get_frame_size(current_spaceship_frame)
    spaceship_position_row, spaceship_position_col = field_size_row // 2, field_size_col // 2
    draw_frame(canvas, spaceship_position_row, spaceship_position_col, current_spaceship_frame)
    old_frame = current_spaceship_frame
    await asyncio.sleep(0.01)
    while True:
        draw_frame(canvas, spaceship_position_row, spaceship_position_col, old_frame, negative=True)
        spaceship_position_row, spaceship_position_col = change_position(
            spaceship_position_row,
            spaceship_position_col,
            spaceship_size_row,
            spaceship_size_col,
            spaceship_speed_row,
            spaceship_speed_col,
            field_size_row,
            field_size_col
        )
        for key in list(active_obstacles.keys()):
            if active_obstacles[key].has_collision(spaceship_position_row, spaceship_position_col,\
                spaceship_size_row, spaceship_size_col):
                await show_gameover(canvas)
                return
        draw_frame(canvas, spaceship_position_row, spaceship_position_col, current_spaceship_frame)
        old_frame = current_spaceship_frame
        await asyncio.sleep(0.1)

async def animate_spaceship2():
    """Change spaceship animation"""
    while True:
        global current_spaceship_frame, old_spaceship_frame
        current_spaceship_frame, old_spaceship_frame = old_spaceship_frame, current_spaceship_frame
        await asyncio.sleep(0.1)

async def handle_buttons(canvas):
    """Handle buttons"""
    global spaceship_speed_row, spaceship_speed_col
    while True:
        delta_speed_row, delta_speed_col, is_fire = read_controls(canvas)
        spaceship_speed_row = spaceship_speed_row + delta_speed_row
        spaceship_speed_col = spaceship_speed_col + delta_speed_col
        if is_fire and year >= 2020:
            asyncio.create_task(fire(canvas, spaceship_position_row, spaceship_position_col + 2))
        await asyncio.sleep(0.01)

async def fly_garbage(canvas, column, garbage_frame, obstacle_id, speed=0.05):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same"""
    rows_number, columns_number = canvas.getmaxyx()
    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0
    obstacle_size_row, obstacle_size_col = get_frame_size(garbage_frame)
    active_obstacles[obstacle_id] = Obstacle(row, column, obstacle_size_row, obstacle_size_col, obstacle_id)
    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0.1)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        if not active_obstacles.get(obstacle_id):
            await explode(canvas, row + obstacle_size_row // 2, column + obstacle_size_col // 2 - 1)
            return
        else:
            active_obstacles[obstacle_id].row += speed
        row += speed

async def fill_orbit_with_garbage(canvas, garbage_animations, row_max):
    """Factory to generate garbage"""
    obstacle_id = 0
    while True:
        tik = get_garbage_delay_tics(year)
        if tik:
            garbage_intension = tik / 5
            garbage_frame = random.choice(list(garbage_animations.values()))
            column = random.randint(2, row_max-2)
            tasks.append(asyncio.create_task(fly_garbage(canvas, column, garbage_frame, obstacle_id, SPEED / 100)))
            obstacle_id += 1
            await asyncio.sleep(garbage_intension)
        else:
            await asyncio.sleep(0.1)


async def show_gameover(canvas):
    """Show gameover"""
    rows_number, columns_number = canvas.getmaxyx()
    go_row, go_col = get_frame_size(GAMEOVER)
    while True:
        draw_frame(canvas, (rows_number - go_row) // 2, (columns_number - go_col) // 2, GAMEOVER)
        await asyncio.sleep(0.1)

async def count_years(text_canvas):
    """Count years"""
    global year
    while True:
        text_canvas.addstr(1, 1, str(year))
        if year in PHRASES:
            text_canvas.addstr(1, 6, PHRASES[year])
        await asyncio.sleep(1.5)
        year += 1

async def refresh_screen(canvas):
    while True:
        canvas.border()
        canvas.refresh()
        await asyncio.sleep(1/60)


async def draw(canvas):
    """Draw all elements
    """
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    canvas_y, cancas_x = canvas.getmaxyx()
    text_canvas = canvas.derwin(3, cancas_x//3, 0, cancas_x//3 * 2)
    canvas_game = canvas.derwin(canvas_y - 3, cancas_x, 3, 0)
    y_max, x_max = canvas_game.getmaxyx()
    garbage = get_garbage_animation()
    for _ in range(100):
        x_cord = random.randint(1, x_max -1)
        y_cord = random.randint(1, y_max -1)
        symbol = random.choice(('+', '*', '.', ':'))
        tasks.append(asyncio.create_task(blink(canvas_game, y_cord, x_cord, symbol)))
    tasks.append(asyncio.create_task(fill_orbit_with_garbage(canvas_game, garbage, x_max)))
    tasks.append(asyncio.create_task(animate_spaceship2()))
    tasks.append(asyncio.create_task(run_spaceship(canvas_game)))
    tasks.append(asyncio.create_task(handle_buttons(canvas)))
    tasks.append(asyncio.create_task(count_years(text_canvas)))
    tasks.append(asyncio.create_task(refresh_screen(canvas)))
    while True:
        while tasks:
            await tasks.pop()
        await asyncio.sleep(0.1)

def wrapped(canvas):
    asyncio.run(draw(canvas), debug=True)

def main():
    try:
        curses.update_lines_cols()
        curses.wrapper(wrapped)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    # asyncio.run(main(),debug=True)
    main()
