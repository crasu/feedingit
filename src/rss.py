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
# Version     : 0.5.0
# Description : Simple RSS Reader
# ============================================================================

from os.path import isfile
from os.path import isdir
from shutil import rmtree
from os import mkdir
import pickle
import md5
import feedparser
import time
import urllib2
from BeautifulSoup import BeautifulSoup
from urlparse import urlparse

#CONFIGDIR="/home/user/.feedingit/"

def getId(string):
    return md5.new(string).hexdigest()

# Entry = {"title":XXX, "content":XXX, "date":XXX, "link":XXX, images = [] }

class ImageHandler:
    def __init__(self, configdir):
        self.configdir = configdir
        self.images = {}
        
    def addImage(self, key, baseurl, url):
        filename = self.configdir+key+".d/"+getId(url)
        if not isfile(filename):
            try:
                if url.startswith("http"):
                    f = urllib2.urlopen(url)
                else:
                    f = urllib2.urlopen(baseurl+"/"+url)
                outf = open(filename, "w")
                outf.write(f.read())
                f.close()
                outf.close()
            except:
                print "Could not download" + url
        if url in self.images:
            self.images[url] += 1
        else:
            self.images[url] = 1
        return "file://" + filename
        
    def removeImage(self, key, url):
        filename = self.configdir+key+".d/"+getId(url)
        self.images[url] -= 1
        if self.images[url] == 0:
            os.remove(filename)
            del self.images[url]

class Feed:
    def __init__(self, uniqueId, name, url, imageHandler):
        self.titles = []
        self.entries = {}
        self.ids = []
        self.readItems = {}
        self.name = name
        self.url = url
        self.countUnread = 0
        self.updateTime = "Never"
        self.uniqueId = uniqueId
        self.imageHandler = imageHandler

    def editFeed(self, url):
        self.url = url

    def saveFeed(self, configdir):
        if not isdir(configdir+self.uniqueId+".d"):
             mkdir(configdir+self.uniqueId+".d")
        file = open(configdir+self.uniqueId+".d/feed", "w")
        pickle.dump(self, file )
        file.close()
        self.saveUnread(configdir)
        
    def saveUnread(self, configdir):
        if not isdir(configdir+self.uniqueId+".d"):
            mkdir(configdir+self.uniqueId+".d")
        file = open(configdir+self.uniqueId+".d/unread", "w")
        pickle.dump(self.readItems, file )
        file.close()

    def reloadUnread(self, configdir):
        try:
            file = open(configdir+self.uniqueId+".d/unread", "r")
            self.readItems = pickle.load( file )
            file.close()
            self.countUnread = 0
            for id in self.getIds():
               if self.readItems[id]==False:
                  self.countUnread = self.countUnread + 1
        except:
            pass
        return self.countUnread

    def updateFeed(self, configdir, expiryTime=24):
        # Expiry time is in hours
        tmp=feedparser.parse(self.url)
        # Check if the parse was succesful (number of entries > 0, else do nothing)
        if len(tmp["entries"])>0:
           #reversedEntries = self.getEntries()
           #reversedEntries.reverse()
           tmpEntries = {}
           tmpIds = []
           for entry in tmp["entries"]:
               (dateTuple, date) = self.extractDate(entry)
               tmpEntry = {"title":entry["title"], "content":self.extractContent(entry),
                            "date":date, "dateTuple":dateTuple, "link":entry["link"], "images":[] }
               id = self.generateUniqueId(tmpEntry)
               tmpEntries[id] = tmpEntry
               tmpIds.append(id)               
           for entryId in self.getIds():
               currentTime = time.time()
               expiry = float(expiryTime) * 3600.
               articleTime = time.mktime(self.entries[entryId]["dateTuple"])
               if currentTime - articleTime < expiry:
                   if not entryId in tmpIds:
                       tmpEntries[entryId] = self.entries[entryId]
                       tmpIds.append(entryId)
               else:
                    if (not self.isEntryRead(entryId)) and (currentTime - articleTime < 2*expiry):
                        tmpEntries[entryId] = self.entries[entryId]
                        tmpIds.append(entryId)
                   
           self.entries = tmpEntries
           self.ids = tmpIds
           self.countUnread = 0
           # Initialize the new articles to unread
           tmpReadItems = self.readItems
           self.readItems = {}
           for id in self.getIds():
               if not tmpReadItems.has_key(id):
                   self.readItems[id] = False
               else:
                   self.readItems[id] = tmpReadItems[id]
               if self.readItems[id]==False:
                  self.countUnread = self.countUnread + 1
           del tmp
           self.updateTime = time.asctime()
           self.saveFeed(configdir)

    def extractContent(self, entry):
        content = ""
        if entry.has_key('summary'):
            content = entry.get('summary', '')
        if entry.has_key('content'):
            if len(entry.content[0].value) > len(content):
                content = entry.content[0].value
        if content == "":
            content = entry.get('description', '')
        return content
        
    def extractDate(self, entry):
        if entry.has_key("updated_parsed"):
            date1 = entry["updated_parsed"]
            date = time.strftime("%a, %d %b %Y %H:%M:%S",entry["updated_parsed"])
        elif entry.has_key("published_parsed"):
            date1 = entry["published_parsed"]
            date = time.strftime("%a, %d %b %Y %H:%M:%S", entry["published_parsed"])
        else:
            date1= ""
            date = ""
        #print date1, date
        return (date1, date)

    def setEntryRead(self, id):
        if self.readItems[id]==False:
            self.countUnread = self.countUnread - 1
            self.readItems[id] = True
            
    def setEntryUnread(self, id):
        if self.readItems[id]==True:
            self.countUnread = self.countUnread + 1
            self.readItems[id] = False
    
    def isEntryRead(self, id):
        return self.readItems[id]
    
    def getTitle(self, id):
        return self.entries[id]["title"]
    
    def getLink(self, id):
        if self.entries[id].has_key("contentLink"):
            return self.entries[id]["contentLink"]
        return self.entries[id]["link"]
    
    def getDate(self, id):
        return self.entries[id]["date"]

    def getDateTuple(self, id):
        return self.entries[id]["dateTuple"]
 
    def getUniqueId(self, index):
        return self.ids[index]
    
    def generateUniqueId(self, entry):
        return getId(entry["date"] + entry["title"])
    
    def getUpdateTime(self):
        return self.updateTime
    
    def getEntries(self):
        return self.entries
    
    def getIds(self):
        return self.ids
    
    def getNextId(self, id):
        return self.ids[(self.ids.index(id)+1) % self.getNumberOfEntries()]
    
    def getPreviousId(self, id):
        return self.ids[(self.ids.index(id)-1) % self.getNumberOfEntries()]
    
    def getNumberOfUnreadItems(self):
        return self.countUnread
    
    def getNumberOfEntries(self):
        return len(self.ids)
    
    def getItem(self, id):
        try:
            return self.entries[id]
        except:
            return []
    
    def getContent(self, id):
        if self.entries[id].has_key("contentLink"):
            file = open(self.entries[id]["contentLink"])
            content = file.read()
            file.close()
            return content
        return self.entries[id]["content"]
    
    def removeEntry(self, id):
        entry = self.entries[id]
        for img in entry["images"]:
            self.imageHandler.removeImage(self.uniqueId, img)
        if entry.has_key["contentLink"]:
            os.remove(entry["contentLink"])
        self.entries.remove(id)
        self.ids.remove(id)
        if self.readItems[id]==False:
            self.countUnread = self.countUnread - 1
        self.readItems.remove(id)
    
    def getArticle(self, id):
        self.setEntryRead(id)
        entry = self.entries[id]
        title = entry['title']
        #content = entry.get('content', entry.get('summary_detail', {}))
        content = entry["content"]

        link = entry['link']
        date = entry["date"]

        #text = '''<div style="color: black; background-color: white;">'''
        text = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
        text += "<html><head><title>" + title + "</title>"
        text += '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>\n'
        #text += '<style> body {-webkit-user-select: none;} </style>'
        text += '</head><body><div><a href=\"' + link + '\">' + title + "</a>"
        text += "<BR /><small><i>Date: " + date + "</i></small></div>"
        text += "<BR /><BR />"
        text += content
        text += "</body></html>"
        return text
        
class ArchivedArticles(Feed):    
    def addArchivedArticle(self, title, link, updated_parsed, configdir):
        entry = {}
        entry["title"] = title
        entry["link"] = link
        entry["summary"] = '<a href=\"' + link + '\">' + title + "</a>"
        entry["updated_parsed"] = updated_parsed
        entry["time"] = time.time()
        #print entry
        (dateTuple, date) = self.extractDate(entry)
        tmpEntry = {"title":entry["title"], "content":self.extractContent(entry),
                            "date":date, "dateTuple":dateTuple, "link":entry["link"], "images":[], "downloaded":False, "time":entry["time"] }
        id = self.generateUniqueId(tmpEntry)
        self.entries[id] = tmpEntry
        self.ids.append(id)  
        self.readItems[id] = False
        self.countUnread = self.countUnread + 1
        self.saveFeed(configdir)
        self.saveUnread(configdir)
        
    def updateFeed(self, configdir, expiryTime=24):
        for id in self.getIds():
            entry = self.entries[id]
            if not entry["downloaded"]:
                #try:
                    f = urllib2.urlopen(entry["link"])
                    #entry["content"] = f.read()
                    html = f.read()
                    f.close()
                    soup = BeautifulSoup(html)
                    images = soup.body('img')
                    baseurl = ''.join(urlparse(entry["link"])[:-1])
                    for img in images:
                        filename = self.imageHandler.addImage(self.uniqueId, baseurl, img['src'])
                        #filename = configdir+self.uniqueId+".d/"+getId(img['src'])
                        #if not isfile(filename):
                        #    try:
                        #        if img['src'].startswith("http"):
                        #            f = urllib2.urlopen(img['src'])
                        #        else:
                        #            f = urllib2.urlopen(baseurl+"/"+img['src'])
                        #            #print baseurl+"/"+img['src']
                        #        print filename
                        #        outf = open(filename, "w")
                        #        outf.write(f.read())
                        #        f.close()
                        #        outf.close()
                        #    except:
                        #        print "Could not download" + img['src']
                        img['src']=filename
                        entry["images"].append(filename)
                    entry["contentLink"] = configdir+self.uniqueId+".d/"+id+".html"
                    file = open(entry["contentLink"], "w")
                    file.write(soup.prettify())
                    file.close()
                    if len(entry["content"]) > 0:
                        entry["downloaded"] = True
                        entry["time"] = time.time()
                        self.setEntryUnread(id)
                #except:
                #    pass
            currentTime = time.time()
            expiry = float(expiryTime) * 3600
            if currentTime - entry["time"] > expiry:
                if self.isEntryRead(id):
                    self.removeEntry(id)
                else:
                    if currentTime - entry["time"] > 2*expiry:
                        self.removeEntry(id)
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
        #self.feeds = {}
        if isfile(self.configdir+"feeds.pickle"):
            file = open(self.configdir+"feeds.pickle")
            self.listOfFeeds = pickle.load(file)
            file.close()
        else:
            self.listOfFeeds = {getId("Slashdot"):{"title":"Slashdot", "url":"http://rss.slashdot.org/Slashdot/slashdot", "unread":0, "updateTime":"Never"}, }
        if isfile(self.configdir+"images.pickle"):
            file = open(self.configdir+"images.pickle")
            self.imageHandler = pickle.load(file)
            file.close()
        else:
            self.imageHandler = ImageHandler(self.configdir)
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
        #for key in list:
        #    try:
        #        self.loadFeed(key)
        #    except:
                #import traceback
                #if key.startswith('d8'):
                #traceback.print_exc()
        #        self.sortedKeys.remove(key)
            #print key
                #print key in self.sortedKeys
        #print "d8eb3f07572892a7b5ed9c81c5bb21a2" in self.sortedKeys
        #print self.listOfFeeds["d8eb3f07572892a7b5ed9c81c5bb21a2"]
        self.closeCurrentlyDisplayedFeed()
        #self.saveConfig()

    def addArchivedArticle(self, key, index):
        feed = self.getFeed(key)
        title = feed.getTitle(index)
        link = feed.getLink(index)
        date = feed.getDateTuple(index)
        if not self.listOfFeeds.has_key("ArchivedArticles"):
            self.listOfFeeds["ArchivedArticles"] = {"title":"Archived Articles", "url":"", "unread":0, "updateTime":"Never"}
            self.sortedKeys.append("ArchivedArticles")
            #self.feeds["Archived Articles"] = ArchivedArticles("Archived Articles", "")
            self.saveConfig()
        archFeed = self.getFeed("ArchivedArticles")
        archFeed.addArchivedArticle(title, link, date, self.configdir)
        self.listOfFeeds[key]["unread"] = archFeed.getNumberOfUnreadItems()
        
    def loadFeed(self, key):
            if isfile(self.configdir+key+".d/feed"):
                file = open(self.configdir+key+".d/feed")
                feed = pickle.load(file)
                file.close()
                try:
                    feed.uniqueId
                    feed.imageHandler
                except AttributeError:
                    feed.uniqueId = getId(feed.name)
                    feed.imageHandler = self.imageHandler
                #feed.reloadUnread(self.configdir)
            else:
                #print key
                title = self.listOfFeeds[key]["title"]
                url = self.listOfFeeds[key]["url"]
                if key == "ArchivedArticles":
                    feed = ArchivedArticles("ArchivedArticles", title, url, self.imageHandler)
                else:
                    feed = Feed(getId(title), title, url, self.imageHandler)
            return feed
        
    def updateFeeds(self, expiryTime=24):
        for key in self.getListOfFeeds():
            feed = self.loadFeed(key)
            feed.updateFeed(self.configdir, expiryTime)
            self.listOfFeeds[key]["unread"] = feed.getNumberOfUnreadItems()
            self.listOfFeeds[key]["updateTime"] = feed.getUpdateTime()
            
    def updateFeed(self, key, expiryTime=24):
        feed = self.loadFeed(key)
        feed.updateFeed(self.configdir, expiryTime)
        self.listOfFeeds[key]["unread"] = feed.getNumberOfUnreadItems()
        self.listOfFeeds[key]["updateTime"] = feed.getUpdateTime()
        
    def editFeed(self, key, title, url):
        self.listOfFeeds[key]["title"] = title
        self.listOfFeeds[key]["url"] = url
        feed = self.loadFeed(key)
        feed.editFeed(url)

    def getFeed(self, key):
        feed = self.loadFeed(key)
        feed.reloadUnread(self.configdir)
        return feed
    
    def getFeedUpdateTime(self, key):
        #print self.listOfFeeds.has_key(key)
        if not self.listOfFeeds[key].has_key("updateTime"):
            self.listOfFeeds[key]["updateTime"] = "Never"
        return self.listOfFeeds[key]["updateTime"]
    
    def getFeedNumberOfUnreadItems(self, key):
        if not self.listOfFeeds[key].has_key("unread"):
            self.listOfFeeds[key]["unread"] = 0
        return self.listOfFeeds[key]["unread"]

    def updateUnread(self, key, unreadItems):
        self.listOfFeeds[key]["unread"] = unreadItems
   
    def getFeedTitle(self, key):
        return self.listOfFeeds[key]["title"]
    
    def getFeedUrl(self, key):
        return self.listOfFeeds[key]["url"]
    
    def getListOfFeeds(self):
        return self.sortedKeys
    
    #def getNumberOfUnreadItems(self, key):
    #    if self.listOfFeeds.has_key("unread"):
    #       return self.listOfFeeds[key]["unread"]
    #    else:
    #       return 0
    
    def addFeed(self, title, url):
        if not self.listOfFeeds.has_key(getId(title)):
            self.listOfFeeds[getId(title)] = {"title":title, "url":url, "unread":0, "updateTime":"Never"}
            self.sortedKeys.append(getId(title))
            self.saveConfig()
            #self.feeds[getId(title)] = Feed(title, url)
            return True
        else:
            return False
        
    def removeFeed(self, key):
        del self.listOfFeeds[key]
        self.sortedKeys.remove(key)
        #del self.feeds[key]
        if isdir(self.configdir+key+".d/"):
           rmtree(self.configdir+key+".d/")
        self.saveConfig()
    
    def saveConfig(self):
        self.listOfFeeds["feedingit-order"] = self.sortedKeys
        file = open(self.configdir+"feeds.pickle", "w")
        pickle.dump(self.listOfFeeds, file)
        file.close()
        file = open(self.configdir+"images.pickle", "w")
        pickle.dump(self.imageHandler, file)
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