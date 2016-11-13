Twitter.indigoPlugin
==================

A [Twitter](http://www.twitter.com) plugin for [Indigo Domotics Indigo 7](http://www.indigodomo.com)

Setup
-----

1. Download and install the twitter indigo plugin
2. Create a twitter account for your indigo server
3. If you want direct message capability then follow your new account and vice versa
4. Visit dev.twitter.com (as your new account) and create an app (a link to further details can be found in the plugin menu)
5. Ensure the twitter app has read, write and direct message permissions
6. Generate api keys for your new application
7. Enter your api key and secret into the configuration UI and click "Get Pin"
8. Enter your account credentials in the new browser window and save the resulting pin provided by Twitter
9. Enter the pin into the configuration UI and click "Get Tokens"
10. Specify trusted twitter users if needed

Tweeting
--------

The plugin provides you with actions to tweet and direct message specific users.  These are available as standard actions as expected.

Responding to Tweets
--------------------

If a (trusted) user sends a  direct message to the indigo twitter account you can configure your indigo instance to respond. Simply create an action group which responds to the text of the user.  So if the incoming request is "alarm status" then create an action group named "twitter\_alarm\_status" and set your actions as you see fit.  If you want to DM back to the user with a response then add a DM action but set the twitter handle to the variable named "currentTWHandle".  This will ensure you respond back to the right user.

Chatbot
-------

This plugin now supports the Indigo Chatbot plugin by gazally.  The plugin can be found on [github](https://github.com/gazally/indigo-chatbot).  Simply choose the checkbox in the configuration and choose the appropriate chatbot device ID.  Any requests which cannot be resolved to known action groups will be forwarded to the chatbot.  Further details on the chatbot plugin can be found at the [Indigo Forum](http://forums.indigodomo.com/viewtopic.php?f=134&t=15535&hilit=chatbot).

Templating
----------

There is a *very* simple templating engine in the plugin to interpolate indigo state into your tweets.  Simple wrap your python expression in ${}.  An example tweet text: "Alarm State: ${indigo.devices['Alarm Panel].states['state']}" or "Bathroom Temperature: ${indigo.devices["Bathroom"].states["temperatureInput1"]}"

To-Do
-----

* Support media tweets so rich media can be sent.