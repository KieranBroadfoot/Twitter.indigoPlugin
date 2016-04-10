Twitter.indigoPlugin
==================

A [Twitter](http://www.twitter.com) plugin for [Perceptive Automation's Indigo 6](http://www.perceptiveautomation.com/indigo/index.html)

Setup
-----

1. Create a twitter account for your indigo server
2. If you want DM capability then follow your new account and vice versa
3. Visit dev.twitter.com (as your new account) and create an app
4. Ensure app has read, write and direct message permissions
5. Generate api keys for your new application
6. sudo easy_install simplejson twitter (we need to do this on the system python, not indigo's python)
7. Download the twitter indigo plugin
8. Before installing cd to Twitter.indigoPlugin/Contents/Server Plugin and run: python setup.py 
9. Enter your api key and secret and wait for the script to fire up your browser to authenticate the twitter account
10. Install the indigo plugin
11. Specify trusted twitter users if needed

Tweeting
--------

The plugin provides you with actions to tweet and direct message specific users.  These are available as standard actions as expected.

Responding to Tweets
--------------------

If a (trusted) users direct messages to the indigo twitter account you can configure your indigo instance to respond. Simply create an action group which responds to the text of the user.  So if the incoming request is "alarm status" then create an action group named "twitter\_alarm\_status" and set your actions as you see fit.  If you want to DM back to the user with a response then add a DM action but set the twitter handle to the variable named "currentTWHandle".  This will ensure you respond back to the right user.

Templating
----------

There is a *very* simple templating engine in the plugin to interpolate indigo state into your tweets.  Simple wrap your python expression in ${}.  An example tweet text: "Alarm State: ${indigo.devices['Alarm Panel].states['state']}" or "Bathroom Temperature: ${indigo.devices["Bathroom"].states["temperatureInput1"]}"

To-Do
-----

* Improve templating (potentially using IWS control pages)
* Consider approaches to convert natural language to actions without the need for triggers
* Tweet images from local cameras
* Wait for Indigo to move to 2.7 to avoid multiple python versions
* Move to zeromq or similar for IPC

Bugs
----

* The plugin currently uses a simple blocking socket for IPC, hence the plugin will not shut down gracefully