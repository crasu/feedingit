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

import gtk
import feedparser
import pango
import hildon
import gtkhtml2
import time
import webbrowser
import pickle
from os.path import isfile, isdir
from os import mkdir
import md5
import sys   

from rss import *
   
class AddWidgetWizard(hildon.WizardDialog):
    
    def __init__(self, parent):
        # Create a Notebook
        self.notebook = gtk.Notebook()

        self.nameEntry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        self.nameEntry.set_placeholder("Enter Feed Name")
        
        self.urlEntry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        
        self.urlEntry.set_placeholder("Enter a URL")
            
        labelEnd = gtk.Label("Success")
        
        self.notebook.append_page(self.nameEntry, None)
        self.notebook.append_page(self.urlEntry, None) 
        self.notebook.append_page(labelEnd, None)      

        hildon.WizardDialog.__init__(self, parent, "Add Feed", self.notebook)
   
        # Set a handler for "switch-page" signal
        #self.notebook.connect("switch_page", self.on_page_switch, self)
   
        # Set a function to decide if user can go to next page
        self.set_forward_page_func(self.some_page_func)
   
        self.show_all()
        print dir(self)
        
    def getData(self):
        return (self.nameEntry.get_text(), self.urlEntry.get_text())
        
    def on_page_switch(self, notebook, page, num, dialog):
        print >>sys.stderr, "Page %d" % num
        return True
   
    def some_page_func(self, nb, current, userdata):
        # Validate data for 1st page
        print current
        if current == 0:
            entry = nb.get_nth_page(current)
            # Check the name is not null
            return len(entry.get_text()) != 0
        elif current == 1:
            entry = nb.get_nth_page(current)
            # Check the url is not null, and starts with http
            print ( (len(entry.get_text()) != 0) and (entry.get_text().startswith("http")) )
            return ( (len(entry.get_text()) != 0) and (entry.get_text().startswith("http")) )
        elif current != 2:
            return False
        else:
            return True

class FeedingIt:
    def __init__(self):
        # Init the windows
        self.window = hildon.StackableWindow()
        menu = hildon.AppMenu()
        # Create a button and add it to the menu
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Update All Feeds")
        button.connect("clicked", self.button_update_clicked, "All")
        menu.append(button)
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Add Feed")
        button.connect("clicked", self.button_add_clicked)
        menu.append(button)
        
        self.window.set_app_menu(menu)
        menu.show_all()
        
        self.feedWindow = hildon.StackableWindow()
        self.articleWindow = hildon.StackableWindow()

        self.listing = Listing()
        #self.listing.downloadFeeds()
        self.displayListing() 
        
        #self.window.show_all()
        #self.displayFeed(self.listing.getFeed(0))
        
    def button_add_clicked(self, button):
        wizard = AddWidgetWizard(self.window)
        ret = wizard.run()
        if ret == 2:
            (title, url) = wizard.getData()
            if (not title == '') and (not url == ''): 
               self.listing.addFeed(title, url)
        wizard.destroy()
        self.displayListing()
        
    def button_update_clicked(self, button, key):
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
        if key == "All":
            self.listing.updateFeeds()
        else:
            self.listing.getFeed(key).updateFeed()
        self.displayListing()
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
        
    def displayListing(self):
        try:
            self.window.remove(self.pannableListing)
        except:
            pass
        self.vboxListing = gtk.VBox(False,10)
        self.pannableListing = hildon.PannableArea()
        self.pannableListing.add_with_viewport(self.vboxListing)

        for key in self.listing.getListOfFeeds():
            #button = gtk.Button(item)
            button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
                              hildon.BUTTON_ARRANGEMENT_VERTICAL)
            button.set_text(self.listing.getFeedTitle(key), self.listing.getFeedUpdateTime(key))
            button.set_alignment(0,0,1,1)
            #label = button.child
            #label.modify_font(pango.FontDescription("sans 10"))
            button.connect("clicked", self.buttonFeedClicked, self, self.window, key)
            self.vboxListing.pack_start(button, expand=False)
        self.window.add(self.pannableListing)
        self.window.show_all()
        
    def displayFeed(self, key):
        # Initialize the feed panel
        self.vboxFeed = gtk.VBox(False, 10)
        self.pannableFeed = hildon.PannableArea()
        self.pannableFeed.add_with_viewport(self.vboxFeed)
        
        index = 0
        for item in self.listing.getFeed(key).getEntries():
            #button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
            #                  hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
            #button.set_text(item["title"], time.strftime("%a, %d %b %Y %H:%M:%S",item["updated_parsed"]))
            #button.set_text(item["title"], time.asctime(item["updated_parsed"]))
            #button.set_text(item["title"],"")
            #button.set_alignment(0,0,1,1)
            #button.set_markup(True)
            button = gtk.Button(item["title"])
            button.set_alignment(0,0)
            label = button.child
            #label.set_markup(item["title"])
            label.modify_font(pango.FontDescription("sans 16"))
            button.connect("clicked", self.button_clicked, self, self.window, key, index)
            self.vboxFeed.pack_start(button, expand=False)
            index=index+1

        self.feedWindow.add(self.pannableFeed)
        self.feedWindow.show_all()
     
    def displayArticle(self, key, index):
        text = self.listing.getFeed(key).getArticle(index)
        self.articleWindow = hildon.StackableWindow()
        # Init the article display    
        self.view = gtkhtml2.View()
        self.document = gtkhtml2.Document()
        self.view.set_document(self.document)
        self.pannable_article = hildon.PannableArea()
        
        #self.view.connect("on_url", self._signal_on_url)
        self.document.connect("link_clicked", self._signal_link_clicked)
        #self.document.connect("request-url", self._signal_request_url)

        self.document.clear()
        self.document.open_stream("text/html")
        self.document.write_stream(text)
        self.document.close_stream()
        
        self.pannable_article.add_with_viewport(self.view)
        self.articleWindow.add(self.pannable_article)
        self.articleWindow.show_all()
     
#    def _signal_on_url(self, object, url):
#        if url == None: url = ""
#        else: url = self._complete_url(url)
        #self.emit("status_changed", url)

    def _signal_link_clicked(self, object, link):
        #self.emit("open_uri", self._complete_url(link))
        #os.spawnl(os.P_NOWAIT, '/usr/bin/browser', '/usr/bin/browser', '--url', link)
        webbrowser.open(link)

#    def _signal_request_url(self, object, url, stream):
#        stream.write(self._fetch_url(self._complete_url(url)))
#        
#    def _complete_url(self, url):
#        import string, urlparse, urllib
#        url = urllib.quote(url, safe=string.punctuation)
#        if urlparse.urlparse(url)[0] == '':
#            return urlparse.urljoin(self.location, url)
#        else:
#            return url
#        
#    def _open_url(self, url, headers=[]):
#        import urllib2
#        opener = urllib2.build_opener()
#        opener.addheaders = [('User-agent', 'Wikitin')]+headers
#        return opener.open(url)
#
#    def _fetch_url(self, url, headers=[]):
#        return self._open_url(url, headers).read()
        
        
    def button_clicked(widget, button, app, window, key, index):
        app.displayArticle(key, index)
    
    def buttonFeedClicked(widget, button, app, window, key):
        app.displayFeed(key)
     
    def run(self):
        self.window.connect("destroy", gtk.main_quit)
        #self.window.show_all()
        gtk.main()

if __name__ == "__main__":
    if not isdir(CONFIGDIR):
        try:
            mkdir(CONFIGDIR)
        except:
            print "Error: Can't create configuration directory"
            sys.exit(1)
    app = FeedingIt()
    app.run()
