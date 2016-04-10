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
        self.chatbotEnabled = False
        self.chatbotID = ''
        self.chatbot = ''

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def startup(self):
        indigo.server.log("starting twitter plugin")
        for trigger in indigo.triggers:
            if trigger.name.startswith("twitter_"):
                indigo.server.log("trigger ("+trigger.name+") no longer supported, use an action group instead")
        if self.pluginPrefs.get("supportChatbot", "false") == True:
            dev = False
            try:
                dev = indigo.devices[int(self.pluginPrefs.get("chatbotID","12345678"))]
            except Exception, e:
                indigo.server.log("invalid chatbot device id.", isError=True)
            if dev:
                chatbotId = "me.gazally.indigoplugin.chatbot"
                self.chatbot = indigo.server.getPlugin(chatbotId)
                self.chatbotEnabled = True
                self.chatbotID = int(self.pluginPrefs.get("chatbotID","12345678"))
                indigo.server.log("chatbot enabled")
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
                            # first: check we havent seen this item before
                            validTweetID = False
                            try:
                                self.lastSeenID = indigo.variables["_twLastSeenID"]
                                if (unpack['id'] > long(self.lastSeenID.value)):
                                    validTweetID = True
                                    indigo.variable.updateValue(self.lastSeenID, str(unpack['id']))
                            except KeyError:
                                # havent seen an ID before.. therefore this is a valid ID.
                                validTweetID = True
                                self.currentHandle = indigo.variable.create("_twLastSeenID", unpack['id'])
                            
                            if validTweetID: 
                                # create a currentTWHandle variable so we can reply.  We presume this plugin is single threaded
                                try:
                                    self.currentHandle = indigo.variables["currentTWHandle"]
                                    indigo.variable.updateValue(self.currentHandle, "@"+unpack['handle'])
                                except KeyError:
                                    self.currentHandle = indigo.variable.create("currentTWHandle", "@"+unpack['handle'])
                                # find valid actionGroup and exec
                                actionGroupName = "twitter_" + re.sub('\s+', '_', unpack['text'].lower())
                                foundTrigger = False
                                collectActionGroups = []
                                for actionGroup in indigo.actionGroups:
                                    if actionGroup.name.startswith("twitter_"):
                                        collectActionGroups.append(actionGroup.name.replace("twitter_","").replace("_"," "))
                                    if actionGroup.name == actionGroupName:
                                        # exec actionGroup
                                        indigo.actionGroup.execute(actionGroup.id)
                                        foundTrigger = True
                        
                                if foundTrigger == False:
                                    # check if text is "help", if so generate a useful response
                                    if unpack['text'].lower() == "help":
                                        self.sendMessageToTWSender(unpack['handle'],"help: "+', '.join(collectActionGroups),"dm")
                                    else:
                                        if self.chatbotEnabled == True and self.chatbot.isEnabled():
                                            props = {"message": unpack['text'], "name": unpack['handle']}
                                            self.chatbot.executeAction("getChatbotResponse", deviceId=self.chatbotID, props=props)
                                        else:
                                            self.sendMessageToTWSender(unpack['handle'],"Sorry Dave, I can't do that","dm")
                            else:
                                indigo.server.log("Tweet containing ID which we've seen before: "+str(unpack['id']))
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
            self.sendMessageToTWSender(h, self.generateResponse(action.props.get("tweetText")), "dm")
        
    def sendTweet(self, action, dev):
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
        segments = []
        if type == "dm":
            indigo.server.log(u"sending direct message to \"%s\": \"%s\"" % (handle, text))
            segments.append(text)
        else:
            # before sending, split into 140 char segments
            indigo.server.log(u"sending tweet \"%s\"" % text)
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
