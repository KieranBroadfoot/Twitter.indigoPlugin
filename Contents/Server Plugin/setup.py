#!/usr/bin/python

APP_CREDS = os.path.expanduser('~/.twitter_app_credentials')
MY_CREDS = os.path.expanduser('~/.twitter_user_credentials')

if not os.path.exists(APP_CREDS):
    key = input('Please enter your consumer key: ')
    secret = input('Please enter your consumer secret: ')
    write_token_file(APP_CREDS, key, secret)
    
if not os.path.exists(MY_CREDS):
    oauth_dance("139jrs", CONSUMER_KEY, CONSUMER_SECRET, MY_CREDS)
    print("Credentials generated. Setup complete")
    sys.exit(0)