import argparse
import asyncio
import logging
import datetime
import sys
import json

from aiofile import AIOFile


async def get_text_from_socket(host, port, async_function, args):
    timer = 0
    try:
        reader, writer = await asyncio.open_connection(host=host,port=port)
    except (ConnectionRefusedError, ConnectionResetError):
        logging.warning('sleep %s seconds', 2 ** timer)
        await asyncio.sleep(2 ** timer)
        reader, writer = await asyncio.open_connection(host=host,port=port)
        timer += 1        
    while True:
        try:
            await async_function(reader, writer, args)
        except (ConnectionRefusedError, ConnectionResetError):
            logging.warning('sleep %s seconds', 2 ** timer)
            await asyncio.sleep(2 ** timer)
            reader, writer = await asyncio.open_connection(host=host,port=port)
            timer += 1


async def read_from_socket(reader, *_):
    text = await reader.readline()
    time_now = datetime.datetime.now().strftime("%y.%m.%d %H.%M")
    async with AIOFile("text.txt", 'a') as _file:
        await _file.write('[{}] {}'.format(time_now, text.decode("utf-8")))
    print(text.decode("utf-8"))


async def send_text_to_socket(reader, writer, args):
    try:
        async with AIOFile(args.token_file, 'r') as _file:
            token = await _file.read()
    except FileNotFoundError:
        token = None
    temp = await reader.readline()
    logging.debug(temp.decode("utf-8"))
    if not token:
        if not args.user:
            logging.error("To connect to the chat please specify the username. it's oblicated only for the first run")
            logging.error('exiting')
            sys.exit()
        writer.write('\n'.encode())
        temp = await reader.readline()
        logging.debug(temp.decode("utf-8"))
        user = '{}\n'.format(args.user)
        writer.write(user.encode())
        answer = await reader.readline()
        logging.debug(answer.decode("utf-8"))
        answer_dict = json.loads(answer)
        token = answer_dict['account_hash']
        logging.debug(token)
        async with AIOFile(args.token_file, 'w') as _file:
            await _file.write(token)
    else:
        writer.write('{}\n'.format(token).encode())
    await asyncio.sleep(2)
    writer.write('{}\n'.format(args.text).encode())
        
async def main():
    parser = argparse.ArgumentParser(description='connect to secret chat')
    parser.add_argument('--host', default='minechat.dvmn.org', help='Host to connect')
    parser.add_argument('--rport', default=5000, type=int, help='Specify port to receive msg')
    parser.add_argument('--sport', default=5050, type=int, help='Specify port to send msg')
    parser.add_argument('--user', help="set a username, it's oblicated for first run")
    parser.add_argument('--token_file', default="token.txt", help="set a file with token")
    parser.add_argument('--text', default="test text", help="set a text to send after registration")

    args = parser.parse_args()
    task_1 = asyncio.create_task(get_text_from_socket(args.host, args.rport, read_from_socket, args))
    task_2 = asyncio.create_task(get_text_from_socket(args.host, args.sport, send_text_to_socket, args))
    await task_1
    await task_2

if __name__ == "__main__":
    asyncio.run(main())