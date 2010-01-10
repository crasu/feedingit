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
# Version     : 0.2.0
# Description : Simple RSS Reader
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
        self.entries = []
        self.readItems = {}
        self.countUnread = 0
        self.name = name
        self.url = url
        self.updateTime = "Never"

    def saveFeed(self):
        file = open(CONFIGDIR+getId(self.name), "w")
        pickle.dump(self, file )
        file.close()

    def updateFeed(self):
        tmp=feedparser.parse(self.url)
        # Check if the parse was succesful (number of entries > 0, else do nothing)
        if len(tmp["entries"])>0:
           self.tmpReadItems = self.readItems
           self.readItems = {}
           self.updateTime = time.asctime()
           self.entries = tmp["entries"]
           self.countUnread = 0
           # Initialize the new articles to unread
           for index in range(self.getNumberOfEntries()):
               if not self.tmpReadItems.has_key(self.getUniqueId(index)):
                   self.readItems[self.getUniqueId(index)] = False
               else:
                   self.readItems[self.getUniqueId(index)] = self.tmpReadItems[self.getUniqueId(index)]
               if self.readItems[self.getUniqueId(index)]==False:
                  self.countUnread = self.countUnread + 1
           del tmp
           self.saveFeed()
    
    def setEntryRead(self, index):
        if self.readItems[self.getUniqueId(index)]==False:
            self.countUnread = self.countUnread - 1
            self.readItems[self.getUniqueId(index)] = True
    
    def isEntryRead(self, index):
        return self.readItems[self.getUniqueId(index)]
    
    def getTitle(self, index):
        return self.entries[index]["title"]
    
    def getUniqueId(self,index):
        entry = self.entries[index]
        return getId(time.strftime("%a, %d %b %Y %H:%M:%S",entry["updated_parsed"]) + entry["title"])
    
    def getUpdateTime(self):
        return self.updateTime
    
    def getEntries(self):
        try:
            return self.entries
        except:
            return []
    
    def getNumberOfUnreadItems(self):
        return self.countUnread
    
    def getNumberOfEntries(self):
        return len(self.entries)
    
    def getItem(self, index):
        try:
            return self.entries[index]
        except:
            return []
    
    def getContent(self, index):
        entry = self.entries[index]
        if entry.has_key('content'):
            content = entry.content[0].value
        else:
            content = entry.get('summary', '')
        return content
    
    def getArticle(self, index):
        self.setEntryRead(index)
        entry = self.entries[index]
        title = entry.get('title', 'No title')
        #content = entry.get('content', entry.get('summary_detail', {}))
        content = self.getContent(index)

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
    def __init__(self):
        self.feeds = {}
        if isfile(CONFIGDIR+"feeds.pickle"):
            file = open(CONFIGDIR+"feeds.pickle")
            self.listOfFeeds = pickle.load(file)
            file.close()
        else:
            self.listOfFeeds = {getId("Slashdot"):{"title":"Slashdot", "url":"http://rss.slashdot.org/Slashdot/slashdot"}, }
        if self.listOfFeeds.has_key("feedingit-order"):
            self.sortedKeys = self.listOfFeeds["feedingit-order"]
        else:
            self.sortedKeys = self.listOfFeeds.keys()
            self.sortedKeys.sort(key=lambda obj: self.getFeedTitle(obj))
        for key in self.sortedKeys:
            if isfile(CONFIGDIR+key):
                file = open(CONFIGDIR+key)
                self.feeds[key] = pickle.load(file)
                file.close()
            else:
                self.feeds[key] = Feed(self.listOfFeeds[key]["title"], self.listOfFeeds[key]["url"])
        self.saveConfig()
        
    def updateFeeds(self):
        for key in self.getListOfFeeds():
            self.feeds[key].updateFeed()
            
    def updateFeed(self, key):
        self.feeds[key].updateFeed()
            
    def getFeed(self, key):
        return self.feeds[key]
    
    def getFeedUpdateTime(self, key):
        return self.feeds[key].getUpdateTime()
    
    def getFeedNumberOfUnreadItems(self, key):
        return self.feeds[key].getNumberOfUnreadItems()
   
    def getFeedTitle(self, key):
        return self.listOfFeeds[key]["title"]
    
    def getFeedUrl(self, key):
        return self.listOfFeeds[key]["url"]
    
    def getListOfFeeds(self):
        return self.sortedKeys
    
    def addFeed(self, title, url):
        self.listOfFeeds[getId(title)] = {"title":title, "url":url}
        self.sortedKeys.append(getId(title))
        self.saveConfig()
        self.feeds[getId(title)] = Feed(title, url)
        
    def removeFeed(self, key):
        del self.listOfFeeds[key]
        self.sortedKeys.remove(key)
        del self.feeds[key]
        if isfile(CONFIGDIR+key):
           remove(CONFIGDIR+key)
    
    def saveConfig(self):
        self.listOfFeeds["feedingit-order"] = self.sortedKeys
        file = open(CONFIGDIR+"feeds.pickle", "w")
        pickle.dump(self.listOfFeeds, file)
        file.close()
        
    def moveUp(self, key):
        index = self.sortedKeys.index(key)
        self.sortedKeys[index] = self.sortedKeys[index-1]
        self.sortedKeys[index-1] = key
        
    def moveDown(self, key):
        index = self.sortedKeys.index(key)
        index2 = (index+1)%len(self.sortedKeys)
        self.sortedKeys[index] = self.sortedKeys[index2]
        self.sortedKeys[index2] = key