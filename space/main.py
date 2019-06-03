import random
import curses
import asyncio

from tools import convert_seconds_to_iterations, get_file, draw_frame, read_controls,\
    change_position, get_frame_size, get_garbage_animation, get_gameover, get_garbage_delay_tics,\
    PHRASES
from obstacles import Obstacle
from explosion import explode
TIMER = 30000
#I don't know how to chose TIMER, and there aren't any information about it in the course materials

SPACESHIP_FRAME1 = get_file('animations/spaceship_frame_1.txt')
SPACESHIP_FRAME2 = get_file('animations/spaceship_frame_2.txt')
CURRENT_SPACESHIP_FRAME = SPACESHIP_FRAME1
OLD_SPACESHIP_FRAME = SPACESHIP_FRAME2
LOOP = asyncio.get_event_loop()
SPACESHIP_SPEED_ROW, SPACESHIP_SPEED_COL = 0, 0
SPACESHIP_POSITION_ROW = 0
SPACESHIP_POSITION_COL = 0
OBSTACLES = {}
GAMEOVER = get_gameover()
YEAR = 1957

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
    canvas.border()
    canvas.refresh()
    # await Sleep(0.1)
    await asyncio.sleep(0.1)
    canvas.addstr(round(row), round(column), 'O')
    canvas.border()
    canvas.refresh()
    # await Sleep(0.1)
    await asyncio.sleep(0.1)
    canvas.addstr(round(row), round(column), ' ')
    canvas.border()
    canvas.refresh()

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        for key in list(OBSTACLES.keys()):
            if OBSTACLES[key].has_collision(round(row), round(column)):
                canvas.addstr(round(row), round(column), ' ')
                OBSTACLES.pop(key)
                return
        canvas.addstr(round(row), round(column), symbol)
        canvas.border()
        canvas.refresh()
        # await Sleep(0.1)
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
            canvas.border()
            canvas.refresh()
            # await Sleep(sleep_time)
            await asyncio.sleep(sleep_time)

async def run_spaceship(canvas):
    global SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL
    field_size_row, field_size_col = canvas.getmaxyx()
    spaceship_size_row, spaceship_size_col = get_frame_size(CURRENT_SPACESHIP_FRAME)
    SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL = field_size_row // 2, field_size_col // 2
    draw_frame(canvas, SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL, CURRENT_SPACESHIP_FRAME)
    canvas.refresh()
    old_frame = CURRENT_SPACESHIP_FRAME
    await asyncio.sleep(0.01)
    while True:
        draw_frame(canvas, SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL, old_frame, negative=True)
        SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL = change_position(
            SPACESHIP_POSITION_ROW,
            SPACESHIP_POSITION_COL,
            spaceship_size_row,
            spaceship_size_col,
            SPACESHIP_SPEED_ROW,
            SPACESHIP_SPEED_COL,
            field_size_row,
            field_size_col
        )
        for key in list(OBSTACLES.keys()):
            if OBSTACLES[key].has_collision(SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL,\
                spaceship_size_row, spaceship_size_col):
                await show_gameover(canvas)
                return
        draw_frame(canvas, SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL, CURRENT_SPACESHIP_FRAME)
        old_frame = CURRENT_SPACESHIP_FRAME
        canvas.refresh()
        await asyncio.sleep(0.1)

async def animate_spaceship2():
    """Change spaceship animation"""
    while True:
        global CURRENT_SPACESHIP_FRAME, OLD_SPACESHIP_FRAME
        CURRENT_SPACESHIP_FRAME, OLD_SPACESHIP_FRAME = OLD_SPACESHIP_FRAME, CURRENT_SPACESHIP_FRAME
        await asyncio.sleep(0.1)

async def handle_buttons(canvas):
    """Handle buttons"""
    global SPACESHIP_SPEED_ROW, SPACESHIP_SPEED_COL
    while True:
        delta_speed_row, delta_speed_col, is_fire = read_controls(canvas)
        SPACESHIP_SPEED_ROW = SPACESHIP_SPEED_ROW + delta_speed_row
        SPACESHIP_SPEED_COL = SPACESHIP_SPEED_COL + delta_speed_col
        if is_fire and YEAR >= 2020:
            LOOP.create_task(fire(canvas, SPACESHIP_POSITION_ROW, SPACESHIP_POSITION_COL + 2))
        await asyncio.sleep(0.01)

async def fly_garbage(canvas, column, garbage_frame, obstacle_id, speed=0.05):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same"""
    rows_number, columns_number = canvas.getmaxyx()
    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0
    obstacle_size_row, obstacle_size_col = get_frame_size(garbage_frame)
    OBSTACLES[obstacle_id] = Obstacle(row, column, obstacle_size_row, obstacle_size_col, obstacle_id)
    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        canvas.border()
        canvas.refresh()
        await asyncio.sleep(0.1)
        # await Sleep(0.1)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        if not OBSTACLES.get(obstacle_id):
            await explode(canvas, row + obstacle_size_row // 2, column + obstacle_size_col // 2 - 1)
            return
        else:
            OBSTACLES[obstacle_id].row += speed
        row += speed

async def fill_orbit_with_garbage(canvas, garbage_animations, row_max):
    """Factory to generate garbage"""
    obstacle_id = 0
    while True:
        tik = get_garbage_delay_tics(YEAR)
        if tik:
            garbage_intension = tik / 5
            garbage_frame = random.choice(list(garbage_animations.values()))
            column = random.randint(2, row_max-2)
            # COROUTINES_TO_ADD.append(fly_garbage(canvas, column, garbage_frame))
            LOOP.create_task(fly_garbage(canvas, column, garbage_frame, obstacle_id))
            obstacle_id += 1
            # await Sleep(garbage_intension)
            await asyncio.sleep(garbage_intension)
        else:
            await asyncio.sleep(0.1)


async def show_gameover(canvas):
    """Show gameover"""
    rows_number, columns_number = canvas.getmaxyx()
    go_row, go_col = get_frame_size(GAMEOVER)
    while True:
        draw_frame(canvas, (rows_number - go_row) // 2, (columns_number - go_col) // 2, GAMEOVER)
        canvas.refresh()
        await asyncio.sleep(0.1)

async def count_years(text_canvas):
    """Count years"""
    global YEAR
    while True:
        text_canvas.addstr(1, 1, str(YEAR))
        if YEAR in PHRASES:
            text_canvas.addstr(1, 6, PHRASES[YEAR])
        text_canvas.refresh()
        await asyncio.sleep(1.5)
        YEAR += 1

# def draw(canvas):
#     """Draw all elements
#     """
#     sleep_times = (2, 0.3, 0.5, 0.3)
#     row, column = (5, 20)
#     canvas.border()
#     canvas.nodelay(True)
#     curses.curs_set(False)
#     coroutines = {}
#     y_max, x_max = canvas.getmaxyx()
#     garbage = get_garbage_animation()
#     for _ in range(100):
#         x_cord = random.randint(1,x_max -1)
#         y_cord = random.randint(1,y_max -1)
#         symbol = random.choice(('+', '*', '.', ':'))
#         coroutines[blink(canvas, y_cord, x_cord, symbol)] = random.randint(0,TIMER)
    # coroutines[fire(canvas, y_max // 2, x_max // 2)] = 0
    # coroutines[animate_spaceship(canvas, y_max // 2, x_max // 2)] = 5
    # coroutines[fill_orbit_with_garbage(canvas, garbage, 1, x_max)] = 0
    # while True:
    #     coroutines_to_remove = []
    #     for coroutine in coroutines:
    #         try:
    #             if coroutines[coroutine] <= 0:
    #                 sleep_seconds = coroutine.send(None).seconds
    #                 sleep_time = convert_seconds_to_iterations(sleep_seconds, TIMER)
    #                 coroutines[coroutine] = sleep_time
    #             coroutines[coroutine] -= 1
    #         except StopIteration:
    #             coroutines_to_remove.append(coroutine)
    #     if coroutines_to_remove:
    #         for coroutine in coroutines_to_remove:
    #             del coroutines[coroutine]
        # if COROUTINES_TO_ADD:
        #     while COROUTINES_TO_ADD:
        #         new_coroutine = COROUTINES_TO_ADD.pop()
        #         coroutines[new_coroutine] = 0
        # canvas.border()
        # canvas.refresh()

def draw_2(canvas):
    """Draw all elements
    """
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    canvas.refresh()
    # coroutines = {}
    canvas_y, cancas_x = canvas.getmaxyx()
    text_canvas = canvas.derwin(3, cancas_x//3, 0, cancas_x//3 * 2)
    text_canvas.border()
    canvas_game = canvas.derwin(canvas_y - 3, cancas_x, 3, 0)
    canvas_game.border()
    y_max, x_max = canvas_game.getmaxyx()
    garbage = get_garbage_animation()
    for _ in range(100):
        x_cord = random.randint(1, x_max -1)
        y_cord = random.randint(1, y_max -1)
        symbol = random.choice(('+', '*', '.', ':'))
        LOOP.create_task(blink(canvas_game, y_cord, x_cord, symbol))
    LOOP.create_task(fill_orbit_with_garbage(canvas_game, garbage, x_max))
    LOOP.create_task(animate_spaceship2())
    LOOP.create_task(run_spaceship(canvas_game))
    LOOP.create_task(handle_buttons(canvas))
    LOOP.create_task(count_years(text_canvas))
    LOOP.run_forever()

def main():
    curses.update_lines_cols()
    curses.wrapper(draw_2)

if __name__ == '__main__':
    main()
