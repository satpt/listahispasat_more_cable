#!/usr/bin/python
# -*- coding: utf-8 -*-

# for localized messages
from . import _
from collections import OrderedDict
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eTimer
from plugin import skin_path, hdr, cfg, common_path, json_file
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap
from xStaticText import StaticText

import json
import time
import xstreamity_globals as glob

import requests
from multiprocessing.pool import ThreadPool


class XStreamity_Menu(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session

		skin = skin_path + 'menu.xml'
		with open(skin, 'r') as f:
			self.skin = f.read()

		#self.startList = []
		self.list = []
		self.drawList = []
		self["list"] = List(self.drawList)

		self.setup_title = (_('Stream Selection'))

		self['key_red'] = StaticText(_('Back'))
		
		self["splash"] = Pixmap()
		self["splash"].show()

		self['actions'] = ActionMap(['XStreamityActions'], {
		'red': self.quit,
		'cancel': self.quit,
		'ok' :  self.next,
		}, -2)

		ref = str(glob.current_playlist['playlist_info']['enigma2_api'])
		self.protocol = glob.current_playlist['playlist_info']['protocol']
		self.domain = glob.current_playlist['playlist_info']['domain']
		self.host = glob.current_playlist['playlist_info']['host']
		self.username = glob.current_playlist['playlist_info']['username']
		self.password = glob.current_playlist['playlist_info']['password']
		self.live_categories_e = "%s/enigma2.php?username=%s&password=%s&type=get_live_categories" % (self.host, self.username, self.password)
		self.live_streams = "%s/player_api.php?username=%s&password=%s&action=get_live_streams" % (self.host, self.username, self.password)

		if ref:
			if not ref.startswith(self.host):
				ref = str(ref.replace(self.protocol + self.domain ,self.host))
				
		# # new player_api code # #
		self.p_live_categories_url =  	"%s/player_api.php?username=%s&password=%s&action=get_live_categories" % (self.host, self.username, self.password)
		self.p_vod_categories_url =  	"%s/player_api.php?username=%s&password=%s&action=get_vod_categories" % (self.host, self.username, self.password)
		self.p_series_categories_url =  "%s/player_api.php?username=%s&password=%s&action=get_series_categories" % (self.host, self.username, self.password)
		self.p_live_streams_url = 		"%s/player_api.php?username=%s&password=%s&action=get_live_streams" % (self.host, self.username, self.password)
		
		glob.current_playlist['data']['live_streams'] = []
		self.onFirstExecBegin.append(self.delayedDownload)
		self.onLayoutFinish.append(self.__layoutFinished)				


	def __layoutFinished(self):
		self.setTitle(self.setup_title)


	#delay to allow splash screen to show
	def delayedDownload(self):
		if glob.current_playlist['data']['live_categories'] == [] and \
			glob.current_playlist['data']['vod_categories'] == [] and \
			glob.current_playlist['data']['series_categories'] == []:
		
			self.timer = eTimer()
			try: 
				self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
			except:
				try:
					self.timer.callback.append(self.makeUrlList)
				except:
					self.makeUrlList()
			self.timer.start(5, True)
			
		else:
			self["splash"].hide()
			self.createSetup()
			
	
	"""		
	def updateCategories(self):
		self["splash"].show()
		glob.current_playlist['data']['live_categories'] = [] 
		glob.current_playlist['data']['vod_categories'] = [] 
		glob.current_playlist['data']['series_categories'] = []
		glob.current_playlist['data']['catchup'] = False
		glob.current_playlist['data']['catchup_checked'] = False
		self.timer = eTimer()
		
		try: 
			self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
		except:
			try:
				self.timer.callback.append(self.makeUrlList)
			except:
				self.makeUrlList()
		self.timer.start(5, True)
		"""
		
		
	def makeUrlList(self):
		self.url_list = []
		self.url_list.append([self.p_live_categories_url, 0])
		self.url_list.append([self.p_vod_categories_url, 1])
		self.url_list.append([self.p_series_categories_url, 2])
		
		if glob.current_playlist['data']['catchup_checked'] == False:
			self.url_list.append([self.p_live_streams_url, 3])	
			glob.current_playlist['data']['catchup_checked'] = True
		
	 	self.process_downloads()
	 	
	 	
	def download_url(self, url):
		timeout = cfg.timeout.getValue()
		category = url[1]
		retries = 9
		r = ''
		
		while True:
			retries -= 1
			try:
				r = requests.get(url[0], headers=hdr, stream=True, timeout=timeout)
				r.raise_for_status()
				if r.status_code == requests.codes.ok:

					"""
					with open(file_name, 'wb') as f:
						for chunk in r.iter_content(chunk_size=8192): 
							f.write(chunk)
							"""
				
					return category, r.json()

			except requests.exceptions.ConnectionError as errc:
				print ("Error Connecting:",errc)
				
				if retries == 0:
					break
				else:
					time.sleep(1)	
		
			except requests.exceptions.RequestException as e:  
				print (e)
				pass
				break
				
		return category, ''
		
			
	def process_downloads(self):
		threads = len(self.url_list)
		results = ThreadPool(threads).imap_unordered(self.download_url, self.url_list)

		for category, response in results:
			if response != '':
				#add categories to main json file		
					if category == 0:
						glob.current_playlist['data']['live_categories'] = response
					elif category == 1:
						glob.current_playlist['data']['vod_categories'] = response
					elif category == 2:
						glob.current_playlist['data']['series_categories'] = response
						
					elif category == 3:
						glob.current_playlist['data']['live_streams'] = response
					
		self["splash"].hide()
		self.createSetup()	
		
			
	def writeJsonFile(self):
		with open(json_file) as f:
			self.playlists_all = json.load(f, object_pairs_hook=OrderedDict)
			
		self.playlists_all[glob.current_selection] =  glob.current_playlist
			
		with open(json_file, 'w') as f:
			json.dump(self.playlists_all, f)
			
			
	def createSetup(self):
		self.list = []
		self.index = 0
		
		if glob.current_playlist['data']['live_categories'] != []:
			self.index += 1
			self.list.append([self.index, "Live Streams", 0, ""])
			
		if glob.current_playlist['data']['vod_categories'] != []:
			self.index += 1
			self.list.append([self.index, "Vod", 1, ""])
			
		if glob.current_playlist['data']['series_categories'] != []:
			self.index += 1
			self.list.append([self.index, "TV Series", 2, ""])

		content = glob.current_playlist['data']['live_streams']
		hascatchup = any(int(item["tv_archive"]) == 1 for item in content if "tv_archive" in item)
		glob.current_playlist['data']['live_streams'] = []
									
		if hascatchup:
			glob.current_playlist['data']['catchup'] = True
			
		if glob.current_playlist['data']['catchup'] == True:
			self.index += 1
			self.list.append([self.index, "Catch Up TV", 3, ""])
		self.drawList = []
		self.drawList = [buildListEntry(x[0],x[1],x[2],x[3]) for x in self.list]
		self["list"].setList(self.drawList)
		
		self.writeJsonFile()
		
		if len(self.list) == 0:
			self.session.openWithCallback(self.close ,MessageBox, _('No data, blocked or playlist not compatible with XStreamity plugin.'), MessageBox.TYPE_WARNING, timeout=5)
		elif len(self.list) == 1:
			self.next()
			self.close()


	def quit(self):
		self.writeJsonFile()
		self.close()


	def next(self):
		import categories
		import catchup
		
		category = self["list"].getCurrent()[2]

		if self["list"].getCurrent():
			if self["list"].getCurrent()[2] == 3:
				self.session.open(catchup.XStreamity_Catchup)
			else:
				self.session.open(categories.XStreamity_Categories, category )		


def buildListEntry(index, title, category_id, playlisturl):
	png = None

	if category_id == 0: png = LoadPixmap(common_path + "live.png")
	if category_id == 1: png = LoadPixmap(common_path + "vod.png")
	if category_id == 2: png = LoadPixmap(common_path + "series.png")
	if category_id == 3: png = LoadPixmap(common_path + "catchup.png")

	return (index, str(title), category_id, str(playlisturl), png)

