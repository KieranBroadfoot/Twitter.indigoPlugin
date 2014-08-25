#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Kieran J. Broadfoot. All rights reserved.
#

################################################################################
# Imports
################################################################################
import sys
import os
import re
import subprocess
import socket
import simplejson as json

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	# Class properties
	########################################
    
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs): 
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.stopThread = False
        self.socket = False
        self.currentHandle = False

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def startup(self):
        indigo.server.log("starting twitter plugin")
        process = subprocess.Popen(["./twrecv.py"], shell=True)
        process = subprocess.Popen(["./twsend.py"], shell=True)

    def stopConcurrentThread(self):
        indigo.server.log("stopping twitter concurrent thread")
        if self.currentHandle != False:
            indigo.variable.delete(self.currentHandle)
        # stop the send/recv scripts
        process = os.system("kill -9 `ps -axo pid,command | grep -v grep | grep twsend | awk '{ print $1 }'`")
        process = os.system("kill -9 `ps -axo pid,command | grep -v grep | grep twrecv | awk '{ print $1 }'`")
    	pass
        
    def runConcurrentThread(self):
        indigo.server.log("starting twitter monitoring thread")
        HOST = ''
        PORT = 13939
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind((HOST, PORT))
            self.socket.listen(5)
            while 1:
                conn, addr = self.socket.accept()
                while True:
                    data = conn.recv(1024)
                    if data:
                        unpack = json.loads(data)
                        
                        # check if incoming message is from a trusted user
                        trustedUsers = self.generateListOfHandles(self.pluginPrefs.get("twitterTrustedUsers", ""))
                        trusted = False;
                        if len(trustedUsers) == 0:
                            trusted = True
                        elif len(trustedUsers) and "@"+unpack['handle'] in trustedUsers:
                                trusted = True
                        if trusted:
                            # first create a currentTWHandle variable
                            try:
                                self.currentHandle = indigo.variables["currentTWHandle"]
                                indigo.variable.updateValue(self.currentHandle, "@"+unpack['handle'])
                            except KeyError:
                                self.currentHandle = indigo.variable.create("currentTWHandle", "@"+unpack['handle'])
                            # find valid trigger and exec
                            triggerName = "twitter_" + re.sub('\s+', '_', unpack['text'].lower())
                            foundTrigger = False
                            collectTriggers = []
                            for trigger in indigo.triggers:
                                if trigger.name.startswith("twitter_"):
                                    collectTriggers.append(trigger.name.replace("twitter_","").replace("_"," "))
                                if trigger.name == triggerName:
                                    # exec trigger
                                    indigo.trigger.execute(trigger.id, ignoreConditions=False)
                                    foundTrigger = True
                        
                            if foundTrigger == False:
                                # check if text is "help", if so generate a useful response
                                if unpack['text'].lower() == "help":
                                    self.sendMessageToTWSender(unpack['handle'],"help: "+', '.join(collectTriggers),"dm")
                                else:
                                    self.sendMessageToTWSender(unpack['handle'],"Sorry Dave, I can't do that","dm")
                        else:
                            indigo.server.log("Tweet from untrusted user: "+"@"+unpack['handle'])
                    else: 
                        break
                conn.close()
        except Exception, e:
            indigo.server.log("closing socket: "+str(e))
            self.socket.close()
            pass
            
    def sendTwitterDirectMessage(self, action, dev):
        for h in self.generateListOfHandles(action.props.get("tweetRecipient","")):
            indigo.server.log(u"sending direct message to \"%s\": \"%s\"" % (h, action.props.get("tweetText","")))
            self.sendMessageToTWSender(h, self.generateResponse(action.props.get("tweetText")), "dm")
        
    def sendTweet(self, action, dev):
        indigo.server.log(u"sending tweet \"%s\"" % (action.props.get("tweetText","")))
        self.sendMessageToTWSender("", self.generateResponse(action.props.get("tweetText")), "tweet")
        
    def generateListOfHandles(self, handleString):
        handles = []
        if len(handleString) == 0:
            return handles
        potentialHandles = handleString.split(",")
        for handle in potentialHandles:
            handle = handle.strip()
            if handle[0] == "@":
                handles.append(handle)
            else:
                for var in indigo.variables:
                    if var.name == handle:
                        potentialHandles.extend(indigo.variables[handle].value.split(","))
        return handles
        
    def sendMessageToTWSender(self, handle, text, type):
        # before sending, split into 140 char segments
        segments = [text[i:i+139] for i in range(0, len(text), 139)]
        host = "127.0.0.1"
        port = 13940
        for segment in segments:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host,port))
            s.send(json.dumps({'handle': handle, 'text': segment, 'type': type}).encode()) 
            s.close()
        
    def generateResponse(self, text):
        # a very simple templating engine to extract IOM expressions
        potential = False
        evaluate = False
        result = ""
        evalstr = ""
        for char in text:
            if char == "$":
                potential = True
            elif char == "{" and potential:
                evaluate = True
            elif char == "}":
                if evaluate:
                    result = result + str(eval(evalstr))
                    evalstr = ""
                    potential = False
                    evaluate = False
                else:
                    # found } but not in eval state
                    result = result + char
            else:
                if evaluate:
                    evalstr = evalstr+char
                else:
                    result = result + char
                    potential = False
        return result