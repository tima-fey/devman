import argparse
import asyncio
import logging
import datetime
import sys
import json

from aiofile import AIOFile


async def read_from_socket(host, port):
    timer = 0
    reader, writer = None, None
    async with AIOFile("text.txt", 'a') as _file:
        while True:
            try:
                if not reader or  not writer:
                    reader, writer = await asyncio.open_connection(host=host, port=port)
                text = await reader.readline()
                time_now = datetime.datetime.now().strftime("%y.%m.%d %H.%M")
                await _file.write('[{}] {}'.format(time_now, text.decode("utf-8")))
                print(text.decode("utf-8"))
            except (ConnectionRefusedError, ConnectionResetError):
                logging.warning('sleep %s seconds', 2 ** timer)
                await asyncio.sleep(2 ** timer)
                reader, writer = None, None
                timer += 1
            except asyncio.CancelledError:
                writer.close()
                raise

async def submit_message(host, port, args):
    timer = 0
    try:
        async with AIOFile(args.token_file, 'r') as _file:
            token = await _file.read()
    except FileNotFoundError:
        token = None
    while True:
        try:
            reader, writer = await asyncio.open_connection(host=host, port=port)
            temp = await reader.readline()
            logging.debug(temp.decode("utf-8"))
            if not token:
                writer.write('\n'.encode())
                await register(reader, writer, args)
            else:
                await authorise(reader, writer, args, token)
            writer.write('{}\n\n'.format(args.text.replace('\n', ' ')).encode())
            logging.info('text has been successfully sent')
            return
        except (ConnectionRefusedError, ConnectionResetError):
            logging.warning('sleep %s seconds', 2 ** timer)
            await asyncio.sleep(2 ** timer)
            timer += 1
        except asyncio.CancelledError:
            writer.close()
            raise

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

async def authorise(reader, writer, args, token):
    writer.write('{}\n'.format(token.replace('\n', '')).encode())
    answer = await reader.readline()
    logging.debug(answer.decode("utf-8"))
    if answer.decode("utf-8") == 'null\n':
        logging.warning("Wrong token, let's get another one")
        await register(reader, writer, args)

async def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='connect to secret chat')
    parser.add_argument('--host', default='minechat.dvmn.org', help='Host to connect')
    parser.add_argument('--rport', default=5000, type=int, help='Specify port to receive msg')
    parser.add_argument('--sport', default=5050, type=int, help='Specify port to send msg')
    parser.add_argument('--user', help="set a username, it's oblicated for first run")
    parser.add_argument('--token_file', default="token.txt", help="set a file with token")
    parser.add_argument('--text', help="set a text to send")
    parser.add_argument('--send_only', action='store_true', help="set a send only mode")


    args = parser.parse_args()
    tasks = []
    if not args.send_only:
        tasks.append(asyncio.create_task(read_from_socket(args.host, args.rport)))
    if args.text:
        tasks.append(asyncio.create_task(submit_message(args.host, args.sport, args)))
    for task in tasks:
        await task

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
