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

twitter_userstream = TwitterStream(auth=auth, domain='userstream.twitter.com')
for msg in twitter_userstream.user():
    if 'direct_message' in msg:
        if msg['direct_message']['sender_screen_name'] != MY_HANDLE:
            # not my own message.
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host = "127.0.0.1"
            port = 13939
            s.connect((host,port))
            s.send(json.dumps({'handle': msg['direct_message']['sender_screen_name'], 
                'text': msg['direct_message']['text'], 
                'type': 'dm'}).encode()) 
            s.close ()