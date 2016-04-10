#!/usr/bin/python

import os
import socket
import simplejson as json
from twitter import *

APP_CREDS = os.path.expanduser('~/.twitter_app_credentials')
MY_CREDS = os.path.expanduser('~/.twitter_user_credentials')

CONSUMER_KEY, CONSUMER_SECRET = read_token_file(APP_CREDS)
oauth_token, oauth_secret = read_token_file(MY_CREDS)

auth = OAuth(
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET,
    token=oauth_token,
    token_secret=oauth_secret
)

twitter = Twitter(auth=auth)

MY_HANDLE = twitter.account.verify_credentials()['screen_name']

HOST = ''
PORT = 13940
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((HOST, PORT))
    s.listen(5)
    while 1:
        conn, addr = s.accept()
        print('Connected with ' + addr[0] + ':' + str(addr[1]))
        while True:
            data = conn.recv(1024)
            # data contains some json.  decode and execute it
            if data: 
                unpack = json.loads(data)
                if unpack['type'] == "tweet":
                    twitter.statuses.update(status=unpack['text'])
                else:
                    try:
                        twitter.direct_messages.new(user=unpack['handle'],text=unpack['text'])
                    except Exception,e:
                        print str(e)
            else:
                break
        conn.close()
    s.close()
except Exception,e: 
    print str(e)
