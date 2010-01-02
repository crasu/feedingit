#!/usr/bin/env python2.5

# 
# Copyright (c) 2007-2008 INdT.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# ============================================================================
# Name        : FeedingIt.py
# Author      : Yves Marcoz
# Version     : 0.1
# Description : PyGtk Example 
# ============================================================================

from os.path import isfile
from os.path import isdir
from os import remove
import pickle
import md5
import feedparser
import time

CONFIGDIR="/home/user/.feedingit/"

def getId(string):
    return md5.new(string).hexdigest()

class Feed:
    # Contains all the info about a single feed (articles, ...), and expose the data
    def __init__(self, name, url):
        self.feed = []
        self.name = name
        self.url = url
        self.updateTime = "Never"
        #self.feed=feedparser.parse(url)
    
    def updateFeed(self):
        tmp=feedparser.parse(self.url)
        if len(tmp["entries"])>0:
           self.feed = tmp
	   self.updateTime = time.asctime()
           file = open(CONFIGDIR+getId(self.name), "w")
           pickle.dump(self, file )
           file.close()
    
    def getUpdateTime(self):
        return self.updateTime
    
    def getEntries(self):
        try:
            return self.feed["entries"]
        except:
            return []
    
    def getItem(self, index):
        try:
            return self.feed["entries"][index]
        except:
            return []
    
    def getArticle(self, index):
        entry = self.feed["entries"][index]
        title = entry.get('title', 'No title')
        #content = entry.get('content', entry.get('summary_detail', {}))
        if entry.has_key('content'):
            content = entry.content[0].value
        else:
            content = entry.get('summary', '')
        #print content.keys()
        #.get('value', "No Data")
        link = entry.get('link', 'NoLink')
        date = time.strftime("%a, %d %b %Y %H:%M:%S",entry["updated_parsed"])
        #text = '''<div style="color: black; background-color: white;">'''
        text = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>'
        text = text + '<div><a href=\"' + link + '\">' + title + "</a>"
        text = text + "<BR /><small><i>Date: " + date + "</i></small></div>"
        text = text + "<BR /><BR />"
        text = text + content
        return text    
    
class Listing:
    # Lists all the feeds in a dictionary, and expose the data
    
    def updateFeeds(self):
        for key in self.listOfFeeds.keys():
            self.feeds[key].updateFeed()
            
    def getFeed(self, key):
        return self.feeds[key]
    
    def getFeedUpdateTime(self, key):
        return self.feeds[key].getUpdateTime()
   
    def getFeedTitle(self, key):
        return self.listOfFeeds[key]["title"]
    
    def getFeedUrl(self, key):
        return self.listOfFeeds[key]["url"]
    
    def getListOfFeeds(self):
        return self.listOfFeeds.keys()
    
    def addFeed(self, title, url):
        self.listOfFeeds[getId(title)] = {"title":title, "url":url}
        self.saveConfig()
        self.feeds[getId(title)] = Feed(title, url)
        
    def removeFeed(self, key):
        del self.listOfFeeds[key]
        del self.feeds[key]
        if isfile(CONFIGDIR+key):
           remove(CONFIGDIR+key)
    
    def saveConfig(self):
        file = open(CONFIGDIR+"feeds.pickle", "w")
        pickle.dump(self.listOfFeeds, file)
        file.close()
    
    def __init__(self):
        self.feeds = {}
        if isfile(CONFIGDIR+"feeds.pickle"):
            file = open(CONFIGDIR+"feeds.pickle")
            self.listOfFeeds = pickle.load(file)
            file.close()
        else:
            self.listOfFeeds = {getId("Slashdot"):{"title":"Slashdot", "url":"http://rss.slashdot.org/Slashdot/slashdot"}, }
        for key in self.listOfFeeds.keys():
            if isfile(CONFIGDIR+key):
                file = open(CONFIGDIR+key)
                self.feeds[key] = pickle.load(file)
                file.close()
            else:
                self.feeds[key] = Feed(self.listOfFeeds[key]["title"], self.listOfFeeds[key]["url"])
        self.saveConfig()