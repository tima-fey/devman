import time
import random
import curses
import asyncio

from tools import convert_seconds_to_iterations, get_file, draw_frame, read_controls, change_position, get_frame_size, get_garbage_animation

TIMER = 30000
#I don't know how to chose TIMER, and there aren't any information about it in the course materials

SPACESHIP_FRAME1 = get_file('animations/spaceship_frame_1.txt')
SPACESHIP_FRAME2 = get_file('animations/spaceship_frame_2.txt')
CURRENT_SPACESHIP_FRAME = SPACESHIP_FRAME1
OLD_SPACESHIP_FRAME = SPACESHIP_FRAME2
LOOP = asyncio.get_event_loop()
SPACESHIP_SPEED_ROW, SPACESHIP_SPEED_COL = 0, 0

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
    await asyncio.sleep(random.randint(0,200)/100)
    actions = ((curses.A_DIM, 2), (curses.A_NORMAL, 0.3), (curses.A_BOLD, 0.5), (curses.A_NORMAL, 0.3))
    while True:
        for (action, sleep_time) in actions:
            canvas.addstr(row, column, symbol, action)
            canvas.border()
            canvas.refresh()
            # await Sleep(sleep_time)
            await asyncio.sleep(sleep_time)

async def run_spaceship(canvas):
    # global CURRENT_SPACESHIP_FRAME
    field_size_row, field_size_col = canvas.getmaxyx()
    spaceship_size_row, spaceship_size_col = get_frame_size(CURRENT_SPACESHIP_FRAME)
    row, column = field_size_row // 2, field_size_col // 2
    draw_frame(canvas, row, column, CURRENT_SPACESHIP_FRAME)
    canvas.refresh()
    old_frame = CURRENT_SPACESHIP_FRAME
    await asyncio.sleep(0.01)
    while True:
        draw_frame(canvas, row, column, old_frame, negative=True)
        row, column = change_position(
            row,
            column,
            spaceship_size_row,
            spaceship_size_col,
            SPACESHIP_SPEED_ROW,
            SPACESHIP_SPEED_COL,
            field_size_row,
            field_size_col
        )
        draw_frame(canvas, row, column, CURRENT_SPACESHIP_FRAME)
        old_frame = CURRENT_SPACESHIP_FRAME
        canvas.refresh()
        await asyncio.sleep(0.1)

async def animate_spaceship2():
    global CURRENT_SPACESHIP_FRAME, OLD_SPACESHIP_FRAME
    CURRENT_SPACESHIP_FRAME, OLD_SPACESHIP_FRAME = OLD_SPACESHIP_FRAME, CURRENT_SPACESHIP_FRAME
    await asyncio.sleep(0.1)

async def handle_buttons(canvas):
    global SPACESHIP_SPEED_ROW, SPACESHIP_SPEED_COL   
    while True:
        delta_speed_row, delta_speed_col, _ = read_controls(canvas)
        SPACESHIP_SPEED_ROW = SPACESHIP_SPEED_ROW + delta_speed_row
        SPACESHIP_SPEED_COL = SPACESHIP_SPEED_COL + delta_speed_col
        await asyncio.sleep(0.01)

async def fly_garbage(canvas, column, garbage_frame, speed=0.05):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        canvas.border()
        canvas.refresh()
        await asyncio.sleep(0.1)
        # await Sleep(0.1)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed

async def fill_orbit_with_garbage(canvas, garbage_animations, garbage_intension, row_max):
    while True:
        garbage_frame = random.choice(list(garbage_animations.values()))
        column = random.randint(2,row_max-2)
        # COROUTINES_TO_ADD.append(fly_garbage(canvas, column, garbage_frame))
        LOOP.create_task(fly_garbage(canvas, column, garbage_frame))
        # await Sleep(garbage_intension)
        await asyncio.sleep(garbage_intension)

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
    sleep_times = (2, 0.3, 0.5, 0.3)
    row, column = (5, 20)
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    canvas.refresh()
    coroutines = {}
    y_max, x_max = canvas.getmaxyx()
    garbage = get_garbage_animation()
    for _ in range(100):
        x_cord = random.randint(1,x_max -1)
        y_cord = random.randint(1,y_max -1)
        symbol = random.choice(('+', '*', '.', ':'))
        LOOP.create_task(blink(canvas, y_cord, x_cord, symbol))
    LOOP.create_task(fire(canvas, y_max // 2, x_max // 2))
    # LOOP.create_task(animate_spaceship(canvas, y_max // 2, x_max // 2))
    LOOP.create_task(fill_orbit_with_garbage(canvas, garbage, 10, x_max))
    LOOP.create_task(animate_spaceship2())
    LOOP.create_task(run_spaceship(canvas))
    LOOP.create_task(handle_buttons(canvas))
    LOOP.run_forever()

def main():
    curses.update_lines_cols()
    curses.wrapper(draw_2)

if __name__ == '__main__':
    main()
