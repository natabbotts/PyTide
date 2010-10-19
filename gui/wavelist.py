#           Licensed to the Apache Software Foundation (ASF) under one
#           or more contributor license agreements.  See the NOTICE file
#           distributed with this work for additional information
#           regarding copyright ownership.  The ASF licenses this file
#           to you under the Apache License, Version 2.0 (the
#           "License"); you may not use this file except in compliance
#           with the License.  You may obtain a copy of the License at

#             http://www.apache.org/licenses/LICENSE-2.0

#           Unless required by applicable law or agreed to in writing,
#           software distributed under the License is distributed on an
#           "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#           KIND, either express or implied.  See the License for the
#           specific language governing permissions and limitations
#           under the License. 

import webgui
import json
import re

from gui import rel_to_abs

withcontact = re.compile("with:(\S*)")

def getContactsFromQuery(query):
	return withcontact.findall(query)

class WaveList(webgui.browserWindow):
	def __init__(self,registry):
		webgui.browserWindow.__init__(self,rel_to_abs("gui/html/wavelist.html"),registry, echo=False)
		self.options = {}
		self.ready = False
		self.getConfig('tbshorten')

	def process(self, data):
		''' Recieve UI input data from window '''
		if data != None:
			if data['type'] == 'query':
				if 'page' in data:
					self.query(data['value'], page=data['page'])
				else:
					self.query(data['value'])
			elif data['type'] == 'sendHTML':
				print data['html']
			elif data['type'] == 'getOptions':
				# Send a dict of all set options
				self.send("pushOptions(%s)" % json.dumps(self.options))
			elif data['type'] == 'setOption':
				# pass on data to other windows and save to config
				self.setConfig(data['key'],data['value'])
			print data
			self.ready = True
		else:
			return None

	def regmsg_receive(self, data):
		''' Recieve message from registry. '''
		if 'type' in data:
			if data['type'] == 'setOption':
				self.options[data['name']] = data['value']
				self.send("pushOption('%s','%s')" % (data['name'],data['value']))
			elif data['type'] == 'kill':
				self.close()
				
		print "Reg >> Wavelist: ",data

	@staticmethod
	def escape(str):
		return str.replace('"','\"')

	def getTitleFromQuery(self, querytext):
		''' Pretty self-explanatory. Takes in a query, returns the appropriate window title for it.'''
		if querytext == "in:inbox":
			return "Inbox"
		elif querytext == "in:all":
			return "Archive"
		elif querytext == "::contacts":
			return "Contacts"
		else: return 'Search "%s"' % querytext

	def query(self, query, page=0):
		'''Send a query to the Network, get a list of results back, and pass it on to the window.'''
		if query == "": 
			query="in:inbox"
		results = self.registry.Network.query(query,startpage=page)
		self.send("clearList()")
		if page!=0:
			pagetext = ", Page "+str(page+1)
		else: pagetext = ""
		self.setTitle(self.getTitleFromQuery(query)+pagetext)
		if results == None:
			self.send("setError('connection')")
			return
		if "::contacts" in query:
			contacts = [{'name':c.name or c.nick,'address':c.addr,'avatar':c.pict} for c in self.registry.Network.getContacts()]
			self.send("contactsList(%s,true)" % json.dumps(contacts))
			return
		else:
			# check for WITH keywords and make a microquery for them
			addresses = getContactsFromQuery(query)
			contacts = []
			for address in addresses:
				contacts += [{'name':c.name or c.nick,'address':c.addr,'avatar':c.pict} for c in self.registry.Network.getContacts()]
			self.send("contactsList(%s, false)" % json.dumps(contacts))
		print results.page, "/", results.maxpage, "\t",results.num_results
		jres = {'query':self.escape(query),'digests':[],'page':results.page,'maxpage':results.maxpage}
		for digest in results.digests:
			plist = digest.participants.serialize()
			participants = [self.registry.Network.participantMeta(x) for x in plist]
			jres['digests'].append({
				'title':self.escape(digest.title),
				'participants':participants,
				'unread':digest.unread_count,
				'total':digest.blip_count,
				'date':digest.last_modified,
				})
		self.send("reloadList(%s, true)" % json.dumps(jres))

	def getConfig(self,key):
		self.options[key] = self.registry.getWaveListConfig(key)
		if self.ready:
			self.send('pushOption("%s","%s")' % (key,self.options[key]))

	def setConfig(self,key, value=None):
		if value != None:
			self.options[key]=value
		self.registry.setWaveListConfig(key, self.options[key])
