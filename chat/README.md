# The minecraft's secret chat client

Connect to 'secret' minecraft chat


## Setup

requre python >= 3.7

```bash
pip install -r requirements.txt
```

## Run

```bash
python chat.py
```
by default server connect to 5000 and 5050 port

## Options

```Bash
python3 chat.py --help
usage: chat.py [-h] [--host HOST] [--rport RPORT] [--sport SPORT]
               [--user USER] [--token_file TOKEN_FILE] [--text TEXT]

connect to secret chat

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           Host to connect
  --rport RPORT         Specify port to receive msg
  --sport SPORT         Specify port to send msg
  --user USER           set a username, it is oblicated for first run
  --token_file TOKEN_FILE
                        set a file with token
  --text TEXT           set a text to send
```

# Project goals

It's just a study project [Devman](https://dvmn.org).