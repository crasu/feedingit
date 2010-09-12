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
# Version     : 0.5.4
# Description : Simple RSS Reader
# ============================================================================

import sqlite3
from os.path import isfile, isdir
from shutil import rmtree
from os import mkdir, remove, utime
import md5
import feedparser
import time
import urllib2
from BeautifulSoup import BeautifulSoup
from urlparse import urljoin
from calendar import timegm

def getId(string):
    return md5.new(string).hexdigest()

class Feed:
    def __init__(self, configdir, key):
        self.key = key
        self.configdir = configdir
        self.dir = "%s/%s.d" %(self.configdir, self.key)
        if not isdir(self.dir):
            mkdir(self.dir)
        if not isfile("%s/%s.db" %(self.dir, self.key)):
            self.db = sqlite3.connect("%s/%s.db" %(self.dir, self.key) )
            self.db.execute("CREATE TABLE feed (id text, title text, contentLink text, date float, updated float, link text, read int);")
            self.db.execute("CREATE TABLE images (id text, imagePath text);")
            self.db.commit()
        else:
            self.db = sqlite3.connect("%s/%s.db" %(self.dir, self.key) )

    def addImage(self, configdir, key, baseurl, url):
        filename = configdir+key+".d/"+getId(url)
        if not isfile(filename):
            try:
                f = urllib2.urlopen(urljoin(baseurl,url))
                outf = open(filename, "w")
                outf.write(f.read())
                f.close()
                outf.close()
            except:
                print "Could not download " + url
        else:
            #open(filename,"a").close()  # "Touch" the file
            file = open(filename,"a")
            utime(filename, None)
            file.close()
        return filename

    def updateFeed(self, configdir, url, etag, modified, expiryTime=24, proxy=None, imageCache=False):
        # Expiry time is in hours
        if proxy == None:
            tmp=feedparser.parse(url, etag = etag, modified = modified)
        else:
            tmp=feedparser.parse(url, etag = etag, modified = modified, handlers = [proxy])
        expiry = float(expiryTime) * 3600.

        currentTime = 0
        # Check if the parse was succesful (number of entries > 0, else do nothing)
        if len(tmp["entries"])>0:
           currentTime = time.time()
           # The etag and modified value should only be updated if the content was not null
           try:
               etag = tmp["etag"]
           except KeyError:
               etag = None
           try:
               modified = tmp["modified"]
           except KeyError:
               modified = None
           try:
               f = urllib2.urlopen(urljoin(tmp["feed"]["link"],"/favicon.ico"))
               data = f.read()
               f.close()
               outf = open(self.dir+"/favicon.ico", "w")
               outf.write(data)
               outf.close()
               del data
           except:
               #import traceback
               #traceback.print_exc()
                pass


           #reversedEntries = self.getEntries()
           #reversedEntries.reverse()

           ids = self.getIds()

           tmp["entries"].reverse()
           for entry in tmp["entries"]:
               date = self.extractDate(entry)
               try:
                   entry["title"]
               except:
                   entry["title"] = "No Title"
               try:
                   entry["link"]
               except:
                   entry["link"] = ""
               try:
                   entry["author"]
               except:
                   entry["author"] = None
               tmpEntry = {"title":entry["title"], "content":self.extractContent(entry),
                            "date":date, "link":entry["link"], "author":entry["author"]}
               id = self.generateUniqueId(tmpEntry)
               
               #articleTime = time.mktime(self.entries[id]["dateTuple"])
               if not id in ids:
                   soup = BeautifulSoup(self.getArticle(tmpEntry)) #tmpEntry["content"])
                   images = soup('img')
                   baseurl = tmpEntry["link"]
                   if imageCache:
                      for img in images:
                          try:
                            filename = self.addImage(configdir, self.key, baseurl, img['src'])
                            img['src']=filename
                            self.db.execute("INSERT INTO images (id, imagePath) VALUES (?, ?);", (id, filename) )
                          except:
                              import traceback
                              traceback.print_exc()
                              print "Error downloading image %s" % img
                   tmpEntry["contentLink"] = configdir+self.key+".d/"+id+".html"
                   file = open(tmpEntry["contentLink"], "w")
                   file.write(soup.prettify())
                   file.close()
                   values = (id, tmpEntry["title"], tmpEntry["contentLink"], tmpEntry["date"], currentTime, tmpEntry["link"], 0)
                   self.db.execute("INSERT INTO feed (id, title, contentLink, date, updated, link, read) VALUES (?, ?, ?, ?, ?, ?, ?);", values)
               else:
                   try:
                       self.db.execute("UPDATE feed SET updated=? WHERE id=?;", (currentTime, id) )
                       self.db.commit()
                       filename = configdir+self.key+".d/"+id+".html"
                       file = open(filename,"a")
                       utime(filename, None)
                       file.close()
                       images = self.db.execute("SELECT imagePath FROM images where id=?;", (id, )).fetchall()
                       for image in images:
                            file = open(image[0],"a")
                            utime(image[0], None)
                            file.close()
                   except:
                       pass
           self.db.commit()
            
           
        rows = self.db.execute("SELECT id FROM feed WHERE (read=0 AND updated<?) OR (read=1 AND updated<?);", (currentTime-2*expiry, currentTime-expiry))
        for row in rows:
           self.removeEntry(row[0])
        
        from glob import glob
        from os import stat
        for file in glob(configdir+self.key+".d/*"):
            #
            stats = stat(file)
            #
            # put the two dates into matching format
            #
            lastmodDate = stats[8]
            #
            expDate = time.time()-expiry*3
            # check if image-last-modified-date is outdated
            #
            if expDate > lastmodDate:
                #
                try:
                    #
                    #print 'Removing', file
                    #
                    remove(file) # commented out for testing
                    #
                except OSError:
                    #
                    print 'Could not remove', file
        updateTime = 0
        rows = self.db.execute("SELECT MAX(date) FROM feed;")
        for row in rows:
            updateTime=row[0]
        return (updateTime, etag, modified)
    
    def setEntryRead(self, id):
        self.db.execute("UPDATE feed SET read=1 WHERE id=?;", (id,) )
        self.db.commit()
        
    def setEntryUnread(self, id):
        self.db.execute("UPDATE feed SET read=0 WHERE id=?;", (id,) )
        self.db.commit()     
        
    def markAllAsRead(self):
        self.db.execute("UPDATE feed SET read=1 WHERE read=0;")
        self.db.commit()

    def isEntryRead(self, id):
        read_status = self.db.execute("SELECT read FROM feed WHERE id=?;", (id,) ).fetchone()[0]
        return read_status==1  # Returns True if read==1, and False if read==0
    
    def getTitle(self, id):
        return self.db.execute("SELECT title FROM feed WHERE id=?;", (id,) ).fetchone()[0]
    
    def getContentLink(self, id):
        return self.db.execute("SELECT contentLink FROM feed WHERE id=?;", (id,) ).fetchone()[0]
    
    def getExternalLink(self, id):
        return self.db.execute("SELECT link FROM feed WHERE id=?;", (id,) ).fetchone()[0]
    
    def getDate(self, id):
        dateStamp = self.db.execute("SELECT date FROM feed WHERE id=?;", (id,) ).fetchone()[0]
        return time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(dateStamp))

    def getDateTuple(self, id):
        dateStamp = self.db.execute("SELECT date FROM feed WHERE id=?;", (id,) ).fetchone()[0]
        return time.localtime(dateStamp)
    
    def getDateStamp(self, id):
        return self.db.execute("SELECT date FROM feed WHERE id=?;", (id,) ).fetchone()[0]
    
    def generateUniqueId(self, entry):
        return getId(str(entry["date"]) + str(entry["title"]))
    
    def getIds(self, onlyUnread=False):
        if onlyUnread:
            rows = self.db.execute("SELECT id FROM feed where read=0 ORDER BY date DESC;").fetchall()
        else:
            rows = self.db.execute("SELECT id FROM feed ORDER BY date DESC;").fetchall()
        ids = []
        for row in rows:
            ids.append(row[0])
        #ids.reverse()
        return ids
    
    def getNextId(self, id):
        ids = self.getIds()
        index = ids.index(id)
        return ids[(index+1)%len(ids)]
        
    def getPreviousId(self, id):
        ids = self.getIds()
        index = ids.index(id)
        return ids[(index-1)%len(ids)]
    
    def getNumberOfUnreadItems(self):
        return self.db.execute("SELECT count(*) FROM feed WHERE read=0;").fetchone()[0]
    
    def getNumberOfEntries(self):
        return self.db.execute("SELECT count(*) FROM feed;").fetchone()[0]

    def getArticle(self, entry):
        #self.setEntryRead(id)
        #entry = self.entries[id]
        title = entry['title']
        #content = entry.get('content', entry.get('summary_detail', {}))
        content = entry["content"]

        link = entry['link']
        author = entry['author']
        date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(entry["date"]) )

        #text = '''<div style="color: black; background-color: white;">'''
        text = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
        text += "<html><head><title>" + title + "</title>"
        text += '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>\n'
        #text += '<style> body {-webkit-user-select: none;} </style>'
        text += '</head><body><div><a href=\"' + link + '\">' + title + "</a>"
        if author != None:
            text += "<BR /><small><i>Author: " + author + "</i></small>"
        text += "<BR /><small><i>Date: " + date + "</i></small></div>"
        text += "<BR /><BR />"
        text += content
        text += "</body></html>"
        return text
   
    def getContent(self, id):
        contentLink = self.db.execute("SELECT contentLink FROM feed WHERE id=?;", (id,)).fetchone()[0]
        try:
            file = open(self.entries[id]["contentLink"])
            content = file.read()
            file.close()
        except:
            content = "Content unavailable"
        return content
    
    def extractDate(self, entry):
        if entry.has_key("updated_parsed"):
            return timegm(entry["updated_parsed"])
        elif entry.has_key("published_parsed"):
            return timegm(entry["published_parsed"])
        else:
            return time.time()
        
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
    
    def removeEntry(self, id):
        contentLink = self.db.execute("SELECT contentLink FROM feed WHERE id=?;", (id,)).fetchone()[0]
        if contentLink:
            try:
                os.remove(contentLink)
            except:
                print "File not found for deletion: %s" % contentLink
        self.db.execute("DELETE FROM feed WHERE id=?;", (id,) )
        self.db.execute("DELETE FROM images WHERE id=?;", (id,) )
        self.db.commit()
 
class ArchivedArticles(Feed):    
    def addArchivedArticle(self, title, link, date, configdir):
        id = self.generateUniqueId({"date":date, "title":title})
        values = (id, title, link, date, 0, link, 0)
        self.db.execute("INSERT INTO feed (id, title, contentLink, date, updated, link, read) VALUES (?, ?, ?, ?, ?, ?, ?);", values)
        self.db.commit()

    def updateFeed(self, configdir, url, etag, modified, expiryTime=24, proxy=None, imageCache=False):
        currentTime = 0
        rows = self.db.execute("SELECT id, link FROM feed WHERE updated=0;")
        for row in rows:
            currentTime = time.time()
            id = row[0]
            link = row[1]
            f = urllib2.urlopen(link)
            #entry["content"] = f.read()
            html = f.read()
            f.close()
            soup = BeautifulSoup(html)
            images = soup('img')
            baseurl = link
            for img in images:
                filename = self.addImage(configdir, self.key, baseurl, img['src'])
                img['src']=filename
                self.db.execute("INSERT INTO images (id, imagePath) VALUES (?, ?);", (id, filename) )
            contentLink = configdir+self.key+".d/"+id+".html"
            file = open(contentLink, "w")
            file.write(soup.prettify())
            file.close()
            
            self.db.execute("UPDATE feed SET read=0, contentLink=?, updated=? WHERE id=?;", (contentLink, time.time(), id) )
            self.db.commit()
        return (currentTime, None, None)
    
    def purgeReadArticles(self):
        rows = self.db.execute("SELECT id FROM feed WHERE read=1;")
        #ids = self.getIds()
        for row in rows:
            self.removeArticle(row[0])

    def removeArticle(self, id):
        rows = self.db.execute("SELECT imagePath FROM images WHERE id=?;", (id,) )
        for row in rows:
            try:
                count = self.db.execute("SELECT count(*) FROM images WHERE id!=? and imagePath=?;", (id,row[0]) ).fetchone()[0]
                if count == 0:
                    os.remove(row[0])
            except:
                pass
        self.removeEntry(id)

class Listing:
    # Lists all the feeds in a dictionary, and expose the data
    def __init__(self, configdir):
        self.configdir = configdir
        
        self.db = sqlite3.connect("%s/feeds.db" % self.configdir)
        
        try:
            table = self.db.execute("SELECT sql FROM sqlite_master").fetchone()
            if table == None:
                self.db.execute("CREATE TABLE feeds(id text, url text, title text, unread int, updateTime float, rank int, etag text, modified text, widget int);")
                if isfile(self.configdir+"feeds.pickle"):
                    self.importOldFormatFeeds()
                else:
                    self.addFeed("Maemo News", "http://maemo.org/news/items.xml")    
            else:
                from string import find, upper
                if find(upper(table[0]), "WIDGET")<0:
                    self.db.execute("ALTER TABLE feeds ADD COLUMN widget int;")
                    self.db.execute("UPDATE feeds SET widget=1;")
                    self.db.commit()
        except:
            pass

    def importOldFormatFeeds(self):
        """This function loads feeds that are saved in an outdated format, and converts them to sqlite"""
        import rss
        listing = rss.Listing(self.configdir)
        rank = 0
        for id in listing.getListOfFeeds():
            try:
                rank += 1
                values = (id, listing.getFeedTitle(id) , listing.getFeedUrl(id), 0, time.time(), rank, None, "None", 1)
                self.db.execute("INSERT INTO feeds (id, title, url, unread, updateTime, rank, etag, modified, widget) VALUES (?, ?, ? ,? ,? ,?, ?, ?, ?);", values)
                self.db.commit()
                
                feed = listing.getFeed(id)
                new_feed = self.getFeed(id)
                
                items = feed.getIds()[:]
                items.reverse()
                for item in items:
                        if feed.isEntryRead(item):
                            read_status = 1
                        else:
                            read_status = 0 
                        date = timegm(feed.getDateTuple(item))
                        title = feed.getTitle(item)
                        newId = new_feed.generateUniqueId({"date":date, "title":title})
                        values = (newId, title , feed.getContentLink(item), date, time.time(), feed.getExternalLink(item), read_status)
                        new_feed.db.execute("INSERT INTO feed (id, title, contentLink, date, updated, link, read) VALUES (?, ?, ?, ?, ?, ?, ?);", values)
                        new_feed.db.commit()
                        try:
                            images = feed.getImages(item)
                            for image in images:
                                new_feed.db.execute("INSERT INTO images (id, imagePath) VALUES (?, ?);", (item, image) )
                                new_feed.db.commit()
                        except:
                            pass
                self.updateUnread(id)
            except:
                import traceback
                traceback.print_exc()
        remove(self.configdir+"feeds.pickle")
                
        
    def addArchivedArticle(self, key, index):
        feed = self.getFeed(key)
        title = feed.getTitle(index)
        link = feed.getExternalLink(index)
        date = feed.getDate(index)
        count = self.db.execute("SELECT count(*) FROM feeds where id=?;", ("ArchivedArticles",) ).fetchone()[0]
        if count == 0:
            self.addFeed("Archived Articles", "", id="ArchivedArticles")

        archFeed = self.getFeed("ArchivedArticles")
        archFeed.addArchivedArticle(title, link, date, self.configdir)
        self.updateUnread("ArchivedArticles")
        
    def updateFeed(self, key, expiryTime=24, proxy=None, imageCache=False):
        feed = self.getFeed(key)
        db = sqlite3.connect("%s/feeds.db" % self.configdir)
        (url, etag, modified) = db.execute("SELECT url, etag, modified FROM feeds WHERE id=?;", (key,) ).fetchone()
        (updateTime, etag, modified) = feed.updateFeed(self.configdir, url, etag, eval(modified), expiryTime, proxy, imageCache)
        if updateTime > 0:
            db.execute("UPDATE feeds SET updateTime=?, etag=?, modified=? WHERE id=?;", (updateTime, etag, str(modified), key) )
        else:
            db.execute("UPDATE feeds SET etag=?, modified=? WHERE id=?;", (etag, str(modified), key) )
        db.commit()
        self.updateUnread(key, db=db)
        
    def getFeed(self, key):
        if key == "ArchivedArticles":
            return ArchivedArticles(self.configdir, key)
        return Feed(self.configdir, key)
        
    def editFeed(self, key, title, url):
        self.db.execute("UPDATE feeds SET title=?, url=? WHERE id=?;", (title, url, key))
        self.db.commit()
        
    def getFeedUpdateTime(self, key):
        return time.ctime(self.db.execute("SELECT updateTime FROM feeds WHERE id=?;", (key,)).fetchone()[0])
        
    def getFeedNumberOfUnreadItems(self, key):
        return self.db.execute("SELECT unread FROM feeds WHERE id=?;", (key,)).fetchone()[0]
        
    def getFeedTitle(self, key):
        return self.db.execute("SELECT title FROM feeds WHERE id=?;", (key,)).fetchone()[0]
        
    def getFeedUrl(self, key):
        return self.db.execute("SELECT url FROM feeds WHERE id=?;", (key,)).fetchone()[0]
        
    def getListOfFeeds(self):
        rows = self.db.execute("SELECT id FROM feeds ORDER BY rank;" )
        keys = []
        for row in rows:
            if row[0]:
                keys.append(row[0])
        return keys
    
    def getSortedListOfKeys(self, order, onlyUnread=False):
        if   order == "Most unread":
            tmp = "ORDER BY unread DESC"
            #keyorder = sorted(feedInfo, key = lambda k: feedInfo[k][1], reverse=True)
        elif order == "Least unread":
            tmp = "ORDER BY unread"
            #keyorder = sorted(feedInfo, key = lambda k: feedInfo[k][1])
        elif order == "Most recent":
            tmp = "ORDER BY updateTime DESC"
            #keyorder = sorted(feedInfo, key = lambda k: feedInfo[k][2], reverse=True)
        elif order == "Least recent":
            tmp = "ORDER BY updateTime"
            #keyorder = sorted(feedInfo, key = lambda k: feedInfo[k][2])
        else: # order == "Manual" or invalid value...
            tmp = "ORDER BY rank"
            #keyorder = sorted(feedInfo, key = lambda k: feedInfo[k][0])
        if onlyUnread:
            sql = "SELECT id FROM feeds WHERE unread>0 " + tmp
        else:
            sql = "SELECT id FROM feeds " + tmp
        rows = self.db.execute(sql)
        keys = []
        for row in rows:
            if row[0]:
                keys.append(row[0])
        return keys
    
    def getFavicon(self, key):
        filename = "%s%s.d/favicon.ico" % (self.configdir, key)
        if isfile(filename):
            return filename
        else:
            return False
        
    def updateUnread(self, key, db=None):
        if db == None:
            db = self.db
        feed = self.getFeed(key)
        db.execute("UPDATE feeds SET unread=? WHERE id=?;", (feed.getNumberOfUnreadItems(), key))
        db.commit()

    def addFeed(self, title, url, id=None):
        if not id:
            id = getId(title)
        count = self.db.execute("SELECT count(*) FROM feeds WHERE id=?;", (id,) ).fetchone()[0]
        if count == 0:
            max_rank = self.db.execute("SELECT MAX(rank) FROM feeds;").fetchone()[0]
            if max_rank == None:
                max_rank = 0
            values = (id, title, url, 0, 0, max_rank+1, None, "None", 1)
            self.db.execute("INSERT INTO feeds (id, title, url, unread, updateTime, rank, etag, modified, widget) VALUES (?, ?, ? ,? ,? ,?, ?, ?, ?);", values)
            self.db.commit()
            # Ask for the feed object, it will create the necessary tables
            self.getFeed(id)
            return True
        else:
            return False
    
    def removeFeed(self, key):
        rank = self.db.execute("SELECT rank FROM feeds WHERE id=?;", (key,) ).fetchone()[0]
        self.db.execute("DELETE FROM feeds WHERE id=?;", (key, ))
        self.db.execute("UPDATE feeds SET rank=rank-1 WHERE rank>?;", (rank,) )
        self.db.commit()

        if isdir(self.configdir+key+".d/"):
           rmtree(self.configdir+key+".d/")
        #self.saveConfig()
        
    #def saveConfig(self):
    #    self.listOfFeeds["feedingit-order"] = self.sortedKeys
    #    file = open(self.configdir+"feeds.pickle", "w")
    #    pickle.dump(self.listOfFeeds, file)
    #    file.close()
        
    def moveUp(self, key):
        rank = self.db.execute("SELECT rank FROM feeds WHERE id=?;", (key,)).fetchone()[0]
        if rank>0:
            self.db.execute("UPDATE feeds SET rank=? WHERE rank=?;", (rank, rank-1) )
            self.db.execute("UPDATE feeds SET rank=? WHERE id=?;", (rank-1, key) )
            self.db.commit()
        
    def moveDown(self, key):
        rank = self.db.execute("SELECT rank FROM feeds WHERE id=?;", (key,)).fetchone()[0]
        max_rank = self.db.execute("SELECT MAX(rank) FROM feeds;").fetchone()[0]
        if rank<max_rank:
            self.db.execute("UPDATE feeds SET rank=? WHERE rank=?;", (rank, rank+1) )
            self.db.execute("UPDATE feeds SET rank=? WHERE id=?;", (rank+1, key) )
            self.db.commit()
            
            
        
