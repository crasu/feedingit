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
# Version     : 0.4.3
# Description : Simple RSS Reader
# ============================================================================

from os.path import isfile
from os.path import isdir
from os import remove
import pickle
import md5
import feedparser
import time
import urllib2

#CONFIGDIR="/home/user/.feedingit/"

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

    def editFeed(self, url):
        self.url = url

    def saveFeed(self, configdir):
        file = open(configdir+getId(self.name), "w")
        pickle.dump(self, file )
        file.close()

    def updateFeed(self, configdir, expiryTime=24):
        # Expiry time is in hours
        tmp=feedparser.parse(self.url)
        # Check if the parse was succesful (number of entries > 0, else do nothing)
        if len(tmp["entries"])>0:
           #reversedEntries = self.getEntries()
           #reversedEntries.reverse()
           tmpIds = []
           for entry in tmp["entries"]:
               tmpIds.append(self.getUniqueId(-1, entry))
           for entry in self.getEntries():
               currentTime = time.time()
               expiry = float(expiryTime) * 3600.
               if entry.has_key("updated_parsed"):
                   articleTime = time.mktime(entry["updated_parsed"])
                   if currentTime - articleTime < expiry:
                       id = self.getUniqueId(-1, entry)
                       if not id in tmpIds:
                           tmp["entries"].append(entry)
                   
           self.entries = tmp["entries"]
           self.countUnread = 0
           # Initialize the new articles to unread
           tmpReadItems = self.readItems
           self.readItems = {}
           for index in range(self.getNumberOfEntries()):
               if not tmpReadItems.has_key(self.getUniqueId(index)):
                   self.readItems[self.getUniqueId(index)] = False
               else:
                   self.readItems[self.getUniqueId(index)] = tmpReadItems[self.getUniqueId(index)]
               if self.readItems[self.getUniqueId(index)]==False:
                  self.countUnread = self.countUnread + 1
           del tmp
           self.updateTime = time.asctime()
           self.saveFeed(configdir)
    
    def setEntryRead(self, index):
        if self.readItems[self.getUniqueId(index)]==False:
            self.countUnread = self.countUnread - 1
            self.readItems[self.getUniqueId(index)] = True
            
    def setEntryUnread(self, index):
        if self.readItems[self.getUniqueId(index)]==True:
            self.countUnread = self.countUnread + 1
            self.readItems[self.getUniqueId(index)] = False
    
    def isEntryRead(self, index):
        return self.readItems[self.getUniqueId(index)]
    
    def getTitle(self, index):
        return self.entries[index]["title"]
    
    def getLink(self, index):
        return self.entries[index]["link"]
    
    def getDate(self, index):
        try:
            return self.entries[index]["updated_parsed"]
        except:
            return time.localtime()
    
    def getUniqueId(self, index, entry=None):
        if index >=0:
            entry = self.entries[index]
        if entry.has_key("updated_parsed"):
            return getId(time.strftime("%a, %d %b %Y %H:%M:%S",entry["updated_parsed"]) + entry["title"])
        elif entry.has_key("link"):
            return getId(entry["link"] + entry["title"])
        else:
            return getId(entry["title"])
    
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
        content = ""
        entry = self.entries[index]
        if entry.has_key('summary'):
            content = entry.get('summary', '')
        if entry.has_key('content'):
            if len(entry.content[0].value) > len(content):
                content = entry.content[0].value
        if content == "":
            content = entry.get('description', '')
        return content
    
    def getArticle(self, index):
        self.setEntryRead(index)
        entry = self.entries[index]
        title = entry.get('title', 'No title')
        #content = entry.get('content', entry.get('summary_detail', {}))
        content = self.getContent(index)

        link = entry.get('link', 'NoLink')
        if entry.has_key("updated_parsed"):
            date = time.strftime("%a, %d %b %Y %H:%M:%S",entry["updated_parsed"])
        elif entry.has_key("published_parsed"):
            date = time.strftime("%a, %d %b %Y %H:%M:%S", entry["published_parsed"])
        else:
            date = ""
        #text = '''<div style="color: black; background-color: white;">'''
        text = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>'
        text += '<head><style> body {-webkit-user-select: none;} </style></head>'
        text += '<body><div><a href=\"' + link + '\">' + title + "</a>"
        text += "<BR /><small><i>Date: " + date + "</i></small></div>"
        text += "<BR /><BR />"
        text += content
        text += "</body>"
        return text

class ArchivedArticles(Feed):
    def addArchivedArticle(self, title, link, updated_parsed, configdir):
        entry = {}
        entry["title"] = title
        entry["link"] = link
        entry["downloaded"] = False
        entry["summary"] = '<a href=\"' + link + '\">' + title + "</a>"
        entry["updated_parsed"] = updated_parsed
        entry["time"] = time.time()
        self.entries.append(entry)
        self.readItems[self.getUniqueId(len(self.entries)-1)] = False
        self.countUnread = self.countUnread + 1
        self.saveFeed(configdir)
        #print entry
        
    def updateFeed(self, configdir, expiryTime=24):
        index = 0
        for entry in self.getEntries():
            if not entry["downloaded"]:
                try:
                    f = urllib2.urlopen(entry["link"])
                    entry["summary"] = f.read()
                    f.close()
                    if len(entry["summary"]) > 0:
                        entry["downloaded"] = True
                        entry["time"] = time.time()
                        self.setEntryUnread(index)
                except:
                    pass
            currentTime = time.time()
            expiry = float(expiryTime) * 3600
            if currentTime - entry["time"] > expiry:
                self.entries.remove(entry)
            index += 1
        self.updateTime = time.asctime()
        self.saveFeed(configdir)

    def getArticle(self, index):
        self.setEntryRead(index)
        content = self.getContent(index)
        return content


class Listing:
    # Lists all the feeds in a dictionary, and expose the data
    def __init__(self, configdir):
        self.configdir = configdir
        self.feeds = {}
        if isfile(self.configdir+"feeds.pickle"):
            file = open(self.configdir+"feeds.pickle")
            self.listOfFeeds = pickle.load(file)
            file.close()
        else:
            self.listOfFeeds = {getId("Slashdot"):{"title":"Slashdot", "url":"http://rss.slashdot.org/Slashdot/slashdot"}, }
        if self.listOfFeeds.has_key("font"):
            del self.listOfFeeds["font"]
        if self.listOfFeeds.has_key("feedingit-order"):
            self.sortedKeys = self.listOfFeeds["feedingit-order"]
        else:
            self.sortedKeys = self.listOfFeeds.keys()
            if "font" in self.sortedKeys:
                self.sortedKeys.remove("font")
            self.sortedKeys.sort(key=lambda obj: self.getFeedTitle(obj))
        list = self.sortedKeys[:]
        for key in list:
            try:
                self.loadFeed(key)
            except:
                #import traceback
                #if key.startswith('d8'):
                #traceback.print_exc()
                self.sortedKeys.remove(key)
            #print key
                #print key in self.sortedKeys
        #print "d8eb3f07572892a7b5ed9c81c5bb21a2" in self.sortedKeys
        #print self.listOfFeeds["d8eb3f07572892a7b5ed9c81c5bb21a2"]
        self.closeCurrentlyDisplayedFeed()
        #self.saveConfig()

    def addArchivedArticle(self, key, index):
        title = self.getFeed(key).getTitle(index)
        link = self.getFeed(key).getLink(index)
        date = self.getFeed(key).getDate(index)
        if not self.listOfFeeds.has_key(getId("Archived Articles")):
            self.listOfFeeds[getId("Archived Articles")] = {"title":"Archived Articles", "url":""}
            self.sortedKeys.append(getId("Archived Articles"))
            self.feeds[getId("Archived Articles")] = ArchivedArticles("Archived Articles", "")
            self.saveConfig()
            
        self.getFeed(getId("Archived Articles")).addArchivedArticle(title, link, date, self.configdir)
        
    def loadFeed(self, key):
            if isfile(self.configdir+key):
                file = open(self.configdir+key)
                self.feeds[key] = pickle.load(file)
                file.close()
            else:
                #print key
                title = self.listOfFeeds[key]["title"]
                url = self.listOfFeeds[key]["url"]
                self.feeds[key] = Feed(title, url)
        
    def updateFeeds(self, expiryTime=24):
        for key in self.getListOfFeeds():
            self.feeds[key].updateFeed(self.configdir, expiryTime)
            
    def updateFeed(self, key, expiryTime=24):
        self.feeds[key].updateFeed(self.configdir, expiryTime)
        
    def editFeed(self, key, title, url):
        self.listOfFeeds[key]["title"] = title
        self.listOfFeeds[key]["url"] = url
        self.feeds[key].editFeed(url)
            
    def getFeed(self, key):
        return self.feeds[key]
    
    def getFeedUpdateTime(self, key):
        #print self.listOfFeeds.has_key(key)
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
        if not self.listOfFeeds.has_key(getId(title)):
            self.listOfFeeds[getId(title)] = {"title":title, "url":url}
            self.sortedKeys.append(getId(title))
            self.saveConfig()
            self.feeds[getId(title)] = Feed(title, url)
            return True
        else:
            return False
        
    def removeFeed(self, key):
        del self.listOfFeeds[key]
        self.sortedKeys.remove(key)
        del self.feeds[key]
        if isfile(self.configdir+key):
           remove(self.configdir+key)
        self.saveConfig()
    
    def saveConfig(self):
        self.listOfFeeds["feedingit-order"] = self.sortedKeys
        file = open(self.configdir+"feeds.pickle", "w")
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
        
    def setCurrentlyDisplayedFeed(self, key):
        self.currentlyDisplayedFeed = key
    def closeCurrentlyDisplayedFeed(self):
        self.currentlyDisplayedFeed = False
    def getCurrentlyDisplayedFeed(self):
        return self.currentlyDisplayedFeed
    
if __name__ == "__main__":
    listing = Listing('/home/user/.feedingit/')
    list = listing.getListOfFeeds()[:]
        #list.reverse()
    for key in list:
        if key.startswith('d8'):
            print listing.getFeedUpdateTime(key)