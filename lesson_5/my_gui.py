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

is_connection_successful = False


class InvalidToken(Exception):
    pass

async def register(reader, writer, args):
    if not args.user:
        logging.error("It's obligated to specidy login if you do not have the correct token file")
        logging.error('exiting')
        sys.exit()
    temp = await reader.readline()
    logging.debug(temp.decode("utf-8"))
    user = '{}\n'.format(args.user.replace('\n', ' '))
    writer.write(user.encode())
    answer = await reader.readline()
    logging.debug(answer.decode("utf-8"))
    answer_dict = json.loads(answer)
    token = answer_dict['account_hash']
    logging.debug(token)
    async with AIOFile(args.token_file, 'w') as _file:
        await _file.write(token)
    return answer_dict['nickname']

async def authorise(reader, writer, token):
    writer.write('{}\n'.format(token.replace('\n', '')).encode())
    answer = await reader.readline()
    decoded_answer = answer.decode("utf-8")
    logging.debug(decoded_answer)
    if decoded_answer == 'null\n':
        logging.warning("Wrong token, let's get another one")
        raise InvalidToken
    answer_dict = json.loads(decoded_answer)
    return answer_dict['nickname']


async def connect_to_receiver(host, port, args, status_updates_queue):
    while True:
        try:
            try:
                async with AIOFile(args.token_file, 'r') as _file:
                    token = await _file.read()
            except FileNotFoundError:
                token = None

            reader, writer = await asyncio.open_connection(host=host, port=port)
            temp = await reader.readline()
            logging.debug(temp.decode("utf-8"))
            if not token:
                writer.write('\n'.encode())
                nickname = await register(reader, writer, args)
            else:
                nickname = await authorise(reader, writer, token)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            status_updates_queue.put_nowait(gui.NicknameReceived(nickname))
            return writer
        except InvalidToken:
            logging.error('invalid token')
            messagebox.showinfo("Invalid token", "Please, check your token, or remove it, to get another one")
            raise
        except (ConnectionRefusedError, ConnectionResetError):
            pass

async def send_msgs(host, port, args, send_queue, store_queue, status_updates_queue, watchdog_queue):
    writer = await connect_to_receiver(host, port, args, status_updates_queue)
    timer = 1
    while True:
        try:
            msg = await send_queue.get()
            if not msg:
                writer.write(''.encode())
                continue
            time_now = datetime.datetime.now().strftime("%y.%m.%d %H.%M")
            msg = '[{}] {}'.format(time_now, msg)
            store_queue.put_nowait(msg)
            watchdog_queue.put_nowait('send msg to server')
            writer.write('{}\n'.format(msg).encode())
            logging.info('text has been successfully sent')
        except (ConnectionRefusedError, ConnectionResetError):
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            logging.warning('sleep %s seconds', 2 ** timer)
            await asyncio.sleep(2 ** timer)
            writer = await connect_to_receiver(host, port, args, status_updates_queue)
            timer += 1
        except asyncio.CancelledError:
            writer.close()
            raise

async def read_from_socket(host, port, messages_queue, status_updates_queue, watchdog_queue):
    timer = 0
    reader, writer = None, None
    while True:
        try:
            if not reader or  not writer:
                reader, writer = await asyncio.open_connection(host=host, port=port)
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            text = await reader.readline()
            time_now = datetime.datetime.now().strftime("%y.%m.%d %H.%M")
            messages_queue.put_nowait('[{}] {}'.format(time_now, text.decode("utf-8")))
            watchdog_queue.put_nowait('get msg from socket')
        except (ConnectionRefusedError, ConnectionResetError):
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            logging.warning('sleep %s seconds', 2 ** timer)
            await asyncio.sleep(2 ** timer)
            reader, writer = None, None
            timer += 1
        except asyncio.CancelledError:
            writer.close()
            raise

async def save_messages(messages_to_file, messages_to_gui, file_name):
    async with AIOFile(file_name, 'a') as _file:
        while True:
            msg = await messages_to_file.get()
            messages_to_gui.put_nowait(msg)
            time_now = datetime.datetime.now().strftime("%y.%m.%d %H.%M")
            await _file.write('[{}] {}'.format(time_now, msg))


async def watchdog(watchdog_queue, logger, time_out):
    global is_connection_successful
    while True:
        try:
            async with async_timeout.timeout(time_out) as timeout_cm:
                msg = await watchdog_queue.get()
                is_connection_successful = True
                logger.info('%s %s', str(datetime.datetime.now()), msg)
        except asyncio.TimeoutError:
            logger.error('timeout expired')
            raise
        # if timeout_cm.expired:
        #     logger.info('timeout expired')

async def handle_connection(args, messages_to_file, status_updates_queue, watchdog_queue, sending_queue, logger, time_out):
    global is_connection_successful
    power_to_sleap = 0
    while True:
        try:
            async with aionursery.Nursery() as nursery:
                nursery.start_soon(read_from_socket(args.host, args.rport, messages_to_file, status_updates_queue, watchdog_queue))
                nursery.start_soon(send_msgs(args.host, args.sport, args, sending_queue, messages_to_file, status_updates_queue, watchdog_queue))
                nursery.start_soon(watchdog(watchdog_queue, logger, time_out))
        except aionursery.MultiError:
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            if is_connection_successful:
                power_to_sleap = 0
            logger.error('reconnect, sleaping %s', 2 ** power_to_sleap)
            await asyncio.sleep(2 ** power_to_sleap)
            power_to_sleap += 1
            is_connection_successful = False


async def ping(time_out, sending_queue):
    while True:
        sending_queue.put_nowait('')
        await asyncio.sleep(time_out / 2)
        
    
async def main():
    time_out = 4
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('watchdog_logger')

    parser = argparse.ArgumentParser(description='connect to secret chat')
    parser.add_argument('--host', default='minechat.dvmn.org', help='Host to connect')
    parser.add_argument('--rport', default=5000, type=int, help='Specify port to receive msg')
    parser.add_argument('--sport', default=5050, type=int, help='Specify port to send msg')
    parser.add_argument('--user', help="set a username, it's oblicated for first run")
    parser.add_argument('--token_file', default="token.txt", help="set a file with token")
    parser.add_argument('--log_file', default="text.txt", help="set file to store text logs")
    args = parser.parse_args()

    messages_to_gui = asyncio.Queue()
    messages_to_file = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)

    with open(args.log_file, 'r') as _file:
        for line in _file.readlines():
            messages_to_gui.put_nowait(line)

    await asyncio.gather(
        gui.draw(messages_to_gui, sending_queue, status_updates_queue),
        handle_connection(args, messages_to_file, status_updates_queue, watchdog_queue, sending_queue, logger, time_out),
        save_messages(messages_to_file, messages_to_gui, args.log_file),
        ping(time_out, sending_queue)
    )
    # async with aionursery.Nursery() as nursery:
    #     nursery.start_soon(asyncio.shield(gui.draw(messages_to_gui, sending_queue, status_updates_queue)))
    #     nursery.start_soon(asyncio.shield(handle_connection(args, messages_to_file, status_updates_queue, watchdog_queue, sending_queue, logger, time_out)))
    #     nursery.start_soon(asyncio.shield(save_messages(messages_to_file, messages_to_gui, args.log_file)))
    #     nursery.start_soon(asyncio.shield(ping(time_out, sending_queue)))
   
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, gui.TkAppClosed, InvalidToken):
        pass
    except Exception:
        pass
