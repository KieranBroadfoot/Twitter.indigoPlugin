#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, Kieran J. Broadfoot. All rights reserved.

import sys
import os
import re
import time
import subprocess
import socket
import simplejson as json
import twitter
from oauthlib import *
from requests_oauthlib import *
import threading
import Queue
import ctypes

class Plugin(indigo.PluginBase):

	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.chatbotEnabled = False
		self.chatbotID = ''
		self.chatbot = ''
		self.twitterAPI = None
		self.stage1OauthToken = ''
		self.stage1OauthSecret = ''
		self.requestToStop = False

	def __del__(self):
		indigo.PluginBase.__del__(self)

	def startup(self):
		self.logger.info("starting twitter plugin")
		indigo.devices.subscribeToChanges()
		for trigger in indigo.triggers:
			if trigger.name.startswith("twitter_"):
				self.logger.error("trigger ("+trigger.name+") no longer supported, use an action group instead")
		self.addChatbotConfiguration(self.pluginPrefs.get("supportChatbot", "false"))
		self.getTwitterAPI(self.pluginPrefs.get("consumerKey", ""),
						   self.pluginPrefs.get("consumerSecret", ""),
						   self.pluginPrefs.get("oauthToken", ""),
						   self.pluginPrefs.get("oauthSecret", ""))

	def shutdown(self):
		self.logger.info("stopping twitter plugin")

	def getTwitterAPI(self, ckey, csecret, otoken, osecret):
		api = twitter.Api(
			consumer_key=ckey,
			consumer_secret=csecret,
			access_token_key=otoken,
			access_token_secret=osecret)
		try:
			creds = api.VerifyCredentials()
			if creds.name:
				self.logger.info("credentials are valid")
				self.twitterAPI = api
				return True
		except Exception, e:
			self.logger.error("credentials are *invalid*")
			return False

	def addChatbotConfiguration(self, state):
		if state == True:
			dev = False
			try:
				dev = indigo.devices[int(self.pluginPrefs.get("chatbotID","12345678"))]
			except Exception, e:
				self.logger.error("invalid chatbot device id.")
			if dev:
				chatbotId = "me.gazally.indigoplugin.chatbot"
				self.chatbot = indigo.server.getPlugin(chatbotId)
				self.chatbotEnabled = True
				self.chatbotID = int(self.pluginPrefs.get("chatbotID","12345678"))
				self.logger.info("chatbot enabled")
		else:
			self.logger.info("chatbot disabled")
			self.chatbotEnabled = False

	def checkboxChanged(self, valuesDict):
		self.addChatbotConfiguration(valuesDict["supportChatbot"])
		return valuesDict

	def oauthStage1ButtonPressed(self, valuesDict):
		self.logger.info("executing OAuth dance (stage 1)...")
		oauth_client = OAuth1Session(valuesDict["consumerKey"], client_secret=valuesDict["consumerSecret"], callback_uri='oob')
		try:
			resp = oauth_client.fetch_request_token("https://api.twitter.com/oauth/request_token")
			self.stage1OauthToken = resp.get('oauth_token')
			self.stage1OauthSecret = resp.get('oauth_token_secret')
			url = oauth_client.authorization_url("https://api.twitter.com/oauth/authorize")
			self.logger.info("opening: "+url)
			self.browserOpen(url)
			self.logger.info("login as "+valuesDict["oauthAppName"]+" and save the resulting pin in the config. Then click 'Get Tokens'")
			valuesDict["stage1CheckBox"] = True
			valuesDict["stage2CheckBox"] = True
		except ValueError as e:
			self.logger.error("Invalid response from Twitter requesting temp token: {0}".format(e))
		return valuesDict

	def oauthStage2ButtonPressed(self, valuesDict):
		self.logger.info("executing OAuth dance (stage 2)...")
		oauth_client = OAuth1Session(valuesDict["consumerKey"], client_secret=valuesDict["consumerSecret"],
							 resource_owner_key=self.stage1OauthToken,
							 resource_owner_secret=self.stage1OauthSecret,
							 verifier=valuesDict["oauthPin"])
		try:
			resp = oauth_client.fetch_access_token("https://api.twitter.com/oauth/access_token")
			valuesDict["oauthToken"] = resp.get('oauth_token')
			valuesDict["oauthSecret"] = resp.get('oauth_token_secret')
			valuesDict["stage2CheckBox"] = True
			valuesDict["stage3CheckBox"] = True
		except ValueError as e:
			self.logger.error("Invalid response from Twitter requesting temp token: {0}".format(e))
		return valuesDict

	def resetAuthentication(self, valuesDict):
		self.logger.info("resetting twitter credentials.")
		self.twitterAPI = False
		valuesDict["oauthPin"] = "Enter pin and click 'Get Tokens'"
		valuesDict["oauthToken"] = ""
		valuesDict["oauthSecret"] = ""
		valuesDict["stage1CheckBox"] = "false"
		valuesDict["stage2CheckBox"] = "false"
		self.logger.info("please restart your plugin.")
		return valuesDict

	def validatePrefsConfigUi(self, valuesDict):
		if self.getTwitterAPI(valuesDict["consumerKey"],valuesDict["consumerSecret"],valuesDict["oauthToken"],valuesDict["oauthSecret"]):
			return True
		else:
			errorDict = indigo.Dict()
			errorDict["consumerKey"] = "Invalid credentials"
			errorDict["consumerSecret"] = "Invalid credentials"
			errorDict["oauthToken"] = "Invalid credentials"
			errorDict["oauthSecret"] = "Invalid credentials"
			return (False, valuesDict, errorDict)

	def deviceUpdated(self, old, new):
		if self.chatbotEnabled == True and new.id == self.chatbotID and new.states["status"] == "Ready":
			# the chatbot has reached a ready state.  that means we need to send a response back
			device = indigo.devices[self.chatbotID]
			reply = device.states["response"]
			typeOfMessage = device.states["info1"]
			handle = device.states["name"]
			self.chatbot.executeAction("clearResponse", deviceId=self.chatbotID, props={})
			if handle != "" and reply != "":
				self.sendMessageToTWSender(handle,reply,typeOfMessage)

	def stopConcurrentThread(self):
		try:
			indigo.variable.delete(indigo.variables["currentTWHandle"])
		except KeyError as e:
			pass
		self.requestToStop = True
		pass

	def runConcurrentThread(self):
		recvQueue = Queue.Queue(30)
		p = TimelineProducer(name='producer', queue=recvQueue, api=self.twitterAPI, logger=self.logger)
		p.start()
		ourUserName = None
		while True:
			while ourUserName == None:
				if self.twitterAPI == None:
					self.sleep(5)
				else:
					creds = self.twitterAPI.VerifyCredentials()
					ourUserName = creds.name
			if self.requestToStop != True:
				if not recvQueue.empty():
					msg = recvQueue.get()
					if msg['direct_message']['sender_screen_name'] != ourUserName:
						# check if incoming message is from a trusted user
						trustedUsers = self.generateListOfHandles(self.pluginPrefs.get("twitterTrustedUsers", ""))
						trusted = False;
						if len(trustedUsers) == 0:
							trusted = True
						elif len(trustedUsers) and "@"+msg['direct_message']['sender_screen_name'] in trustedUsers:
							trusted = True
						if trusted:
							# first: check we havent seen this item before
							validTweetID = False
							try:
								self.lastSeenID = indigo.variables["_twLastSeenID"]
								if (msg['direct_message']['id'] > long(self.lastSeenID.value)):
									validTweetID = True
									indigo.variable.updateValue(self.lastSeenID, str(msg['direct_message']['id']))
							except KeyError:
								# havent seen an ID before.. therefore this is a valid ID.
								validTweetID = True
								indigo.variable.create("_twLastSeenID", str(msg['direct_message']['id']))
							if validTweetID:
								# create a currentTWHandle variable so we can reply.  We presume this plugin is single threaded
								try:
									currentHandle = indigo.variables["currentTWHandle"]
									indigo.variable.updateValue(currentHandle, "@"+msg['direct_message']['sender_screen_name'])
								except KeyError:
									indigo.variable.create("currentTWHandle", "@"+msg['direct_message']['sender_screen_name'])
								# find valid actionGroup and exec
								actionGroupName = "twitter_" + re.sub('\s+', '_', msg['direct_message']['text'].lower())
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
									if msg['direct_message']['text'].lower() == "help":
										self.sendMessageToTWSender(msg['direct_message']['sender_screen_name'],"help: "+', '.join(collectActionGroups),"dm")
									else:
										if self.chatbotEnabled == True and self.chatbot.isEnabled():
											props = {"message": msg['direct_message']['text'], "name": msg['direct_message']['sender_screen_name'], "info1": "dm"}
											self.chatbot.executeAction("getChatbotResponse", deviceId=self.chatbotID, props=props)
										else:
											self.sendMessageToTWSender(msg['direct_message']['sender_screen_name'],"Sorry Dave, I can't do that","dm")
							else:
								self.logger.info("tweet seen before: "+msg['direct_message']['id'])
						else:
							self.logger.info("tweet from untrusted user: "+"@"+msg['direct_message']['sender_screen_name'])
				else:
					self.sleep(1)
			else:
				p.terminate()
				return

	def sendMessageToTWSender(self, handle, text, type):
		if self.twitterAPI:
			text = self.generateResponse(text)
			if type == "dm":
				self.logger.info(u"sending direct message to \"%s\": \"%s\"" % (handle, text))
				try:
					status = self.twitterAPI.PostDirectMessage(text, screen_name=handle)
				except Exception, e:
					self.logger.error(e.message)
			else:
				# before sending, split into 140 char segments
				self.logger.info(u"sending tweet \"%s\"" % text)
				segments = [text[i:i+139] for i in range(0, len(text), 139)]
				for segment in segments:
					try:
						status = api.PostUpdate(segment)
					except Exception, e:
						self.logger.error(e.message)
		else:
			self.logger.error("no valid twitter credentials; ignoring request")

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

	def accessDevTwitter(self):
		self.browserOpen("https://dev.twitter.com/oauth/overview/application-owner-access-tokens")

class TimelineProducer(threading.Thread):
	def __init__(self, group=None, target=None, name=None, queue=None, api=None, logger=None,
				args=(), kwargs=None, verbose=None):
		super(TimelineProducer,self).__init__()
		self._stop = threading.Event()
		self.target = target
		self.name = name
		self.queue = queue
		self.api = api
		self.logger = logger

	def run(self):
		while True:
			if self.api:
				self.logger.info("starting twitter monitoring thread")
				try:
					stream = self.api.GetUserStream()
					for msg in stream:
						if 'direct_message' in msg:
							if not self.queue.full():
								self.queue.put(msg)
				except Exception, e:
					self.logger.warn("received monitoring error from twitter: "+str(e))

	def getTid(self):
		for tid, tobj in threading._active.items():
			if tobj is self:
				return tid

	def terminate(self):
		tid = self.getTid()
		res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(SystemExit))
		if res == 0:
			self.logger.warn("failed to shutdown monitoring thread")
		elif res != 1:
			self.logger.warn("failed to shutdown monitoring thread (attempting to fix)")
			ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)