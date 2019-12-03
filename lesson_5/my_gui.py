import asyncio
import sys
import logging
import datetime
import argparse
import json
from tkinter import messagebox

from aiofile import AIOFile
import async_timeout
import aionursery

import gui

class InvalidToken(Exception):
    pass

async def register(reader, writer, user, token_file):
    logger = logging.getLogger('watchdog_logger')
    temp = await reader.readline()
    logger.debug(temp.decode("utf-8"))
    writer.write(user.encode())
    await writer.drain()
    answer = await reader.readline()
    logger.debug(answer.decode("utf-8"))
    answer_dict = json.loads(answer)
    token = answer_dict['account_hash']
    logger.debug(token)
    async with AIOFile(token_file, 'w') as _file:
        await _file.write(token)
    return answer_dict['nickname']

async def authorise(reader, writer, token):
    logger = logging.getLogger('watchdog_logger')
    writer.write('{}\n'.format(token.replace('\n', '')).encode())
    await writer.drain()
    answer = await reader.readline()
    decoded_answer = answer.decode("utf-8")
    logger.debug(decoded_answer)
    if decoded_answer == 'null\n':
        logger.warning("Wrong token, let's get another one")
        raise InvalidToken
    answer_dict = json.loads(decoded_answer)
    return answer_dict['nickname']

async def connect_to_receiver(host, port, status_updates_queue, user, token_file, token):
    logger = logging.getLogger('watchdog_logger')
    while True:
        try:
            reader, writer = await asyncio.open_connection(host=host, port=port)
            temp = await reader.readline()
            logger.debug(temp.decode("utf-8"))
            if not token:
                writer.write('\n'.encode())
                nickname = await register(reader, writer, user, token_file)
            else:
                nickname = await authorise(reader, writer, token)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            status_updates_queue.put_nowait(gui.NicknameReceived(nickname))
            return writer
        except InvalidToken:
            logger.error('invalid token')
            messagebox.showinfo("Invalid token", "Please, check your token, or remove it, to get another one")
            raise


async def send_msgs(host, port, send_queue, store_queue, status_updates_queue, watchdog_queue, user, token_file, token):
    logger = logging.getLogger('watchdog_logger')
    writer = await connect_to_receiver(host, port, status_updates_queue, user, token_file, token)
    await writer.drain()
    power_to_sleap = 0
    while True:
        try:
            msg = await send_queue.get()
            if not msg:
                writer.write(''.encode())                                         # send ping
                continue
            time_now = datetime.datetime.now().strftime("%y.%m.%d %H.%M")
            msg = '[{}] {}'.format(time_now, msg)
            store_queue.put_nowait('{}\n'.format(msg))
            watchdog_queue.put_nowait('send msg to server')
            writer.write('{}\n'.format(msg).encode())
            await writer.drain()
            logger.info('text has been successfully sent')
        except aionursery.MultiError:
            writer.close()
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            await asyncio.sleep(2 ** power_to_sleap)
            power_to_sleap += 1
        except asyncio.CancelledError:
            writer.close()
        else:
            power_to_sleap = 0

async def read_from_socket(host, port, messages_queue, status_updates_queue, watchdog_queue):
    reader, writer = None, None
    power_to_sleap = 0
    while True:
        try:
            if not reader or  not writer:
                reader, writer = await asyncio.open_connection(host=host, port=port)
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            text = await reader.readline()
            time_now = datetime.datetime.now().strftime("%y.%m.%d %H.%M")
            messages_queue.put_nowait('[{}] {}'.format(time_now, text.decode("utf-8")))
            watchdog_queue.put_nowait('get msg from socket')
        except aionursery.MultiError:
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            await asyncio.sleep(2 ** power_to_sleap)
            power_to_sleap += 1
        except asyncio.CancelledError:
            raise
        else:
            power_to_sleap = 0

async def save_messages(messages_to_file, messages_to_gui, file_name):
    async with AIOFile(file_name, 'a') as _file:
        while True:
            msg = await messages_to_file.get()
            messages_to_gui.put_nowait(msg)
            await _file.write(msg)


async def watchdog(watchdog_queue, time_out, status_updates_queue):
    logger = logging.getLogger('watchdog_logger')
    power_to_sleap = 0
    while True:
        try:
            async with async_timeout.timeout(time_out):
                _ = await watchdog_queue.get()
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        except asyncio.TimeoutError:
            logger.error('timeout expired')
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            await asyncio.sleep(2 ** power_to_sleap)
            power_to_sleap += 1
        else:
            power_to_sleap = 0

async def handle_connection(messages_to_file, status_updates_queue, watchdog_queue, sending_queue, time_out, user, host, rport, sport, token_file, token):
    while True:
        async with aionursery.Nursery() as nursery:
            nursery.start_soon(read_from_socket(host, rport, messages_to_file, status_updates_queue, watchdog_queue))
            nursery.start_soon(send_msgs(host, sport, sending_queue, messages_to_file, status_updates_queue, watchdog_queue, user, token_file, token))
            nursery.start_soon(watchdog(watchdog_queue, time_out, status_updates_queue))


async def ping(time_out, sending_queue):
    while True:
        sending_queue.put_nowait('')
        await asyncio.sleep(time_out / 2)

async def main():
    time_out = 4
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger('watchdog_logger')

    parser = argparse.ArgumentParser(description='connect to secret chat')
    parser.add_argument('--host', default='minechat.dvmn.org', help='Host to connect')
    parser.add_argument('--rport', default=5000, type=int, help='Specify port to receive msg')
    parser.add_argument('--sport', default=5050, type=int, help='Specify port to send msg')
    parser.add_argument('--user', help="set a username, it's oblicated for first run")
    parser.add_argument('--token_file', default="token.txt", help="set a file with token")
    parser.add_argument('--log_file', default="text.txt", help="set file to store text logs")
    args = parser.parse_args()
    try:
        with open(args.token_file, 'r') as _file:
            token = _file.read()
    except FileNotFoundError:
        token = None
    if not args.user and not token:
        logger.error("It's obligated to specidy login if you do not have the correct token file")
        logger.error('exiting')
        sys.exit()
    if args.user:
        user = '{}\n'.format(args.user.replace('\n', ' '))
    else:
        user = None

    messages_to_gui = asyncio.Queue()
    messages_to_file = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    try:
        with open(args.log_file, 'r') as _file:
            for line in _file.readlines():
                messages_to_gui.put_nowait(line)
    except FileNotFoundError:
        pass

    async with aionursery.Nursery() as nursery:
        nursery.start_soon(gui.draw(messages_to_gui, sending_queue, status_updates_queue))
        nursery.start_soon(handle_connection(
            messages_to_file,
            status_updates_queue,
            watchdog_queue,
            sending_queue,
            time_out,
            user,
            args.host,
            args.rport,
            args.sport,
            args.token_file,
            token))
        nursery.start_soon(save_messages(messages_to_file, messages_to_gui, args.log_file))
        nursery.start_soon(ping(time_out, sending_queue))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, gui.TkAppClosed, InvalidToken):
        sys.exit()
