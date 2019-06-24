import subprocess
import asyncio
import time

# archive = subprocess.check_output(['zip', '-r', '-', 'test.txt'])
# with open('test1.zip', 'wb') as fl:
#     fl.write(archive)




async def unzip(files):
    cmd = 'zip -r - {} >'.format(files)
    # proc = await asyncio.create_subprocess_shell(
    #     cmd,
    #     stdout=asyncio.subprocess.PIPE,
    #     stderr=asyncio.subprocess.PIPE)
    proc = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', 'test.txt',
        stdout=asyncio.subprocess.PIPE)
    with open('test1.zip', 'wb') as fl:
        while True:
            data = await proc.stdout.readline()
            if data:
                print(data)
                # stdout, stderr = await proc.communicate()
                fl.write(data)
            else:
                break
    

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(
    unzip('test.txt'),
    ))
loop.close()