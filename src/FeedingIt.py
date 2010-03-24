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

import gtk
import feedparser
import pango
import hildon
#import gtkhtml2
#try:
import webkit
#    has_webkit=True
#except:
#    import gtkhtml2
#    has_webkit=False
import time
import dbus
import pickle
from os.path import isfile, isdir
from os import mkdir
import sys   
import urllib2
import gobject
from portrait import FremantleRotation
import threading
import thread
from feedingitdbus import ServerObject
from config import Config

from rss import *
from opml import GetOpmlData, ExportOpmlData
   
import socket
timeout = 5
socket.setdefaulttimeout(timeout)

color_style = gtk.rc_get_style_by_paths(gtk.settings_get_default() , 'GtkButton', 'osso-logical-colors', gtk.Button)
unread_color = color_style.lookup_color('ActiveTextColor')
read_color = color_style.lookup_color('DefaultTextColor')
del color_style

CONFIGDIR="/home/user/.feedingit/"

class AddWidgetWizard(hildon.WizardDialog):
    
    def __init__(self, parent, urlIn, titleIn=None):
        # Create a Notebook
        self.notebook = gtk.Notebook()

        self.nameEntry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        self.nameEntry.set_placeholder("Enter Feed Name")
        vbox = gtk.VBox(False,10)
        label = gtk.Label("Enter Feed Name:")
        vbox.pack_start(label)
        vbox.pack_start(self.nameEntry)
        if not titleIn == None:
            self.nameEntry.set_text(titleIn)
        self.notebook.append_page(vbox, None)
        
        self.urlEntry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        self.urlEntry.set_placeholder("Enter a URL")
        self.urlEntry.set_text(urlIn)
        self.urlEntry.select_region(0,-1)
        
        vbox = gtk.VBox(False,10)
        label = gtk.Label("Enter Feed URL:")
        vbox.pack_start(label)
        vbox.pack_start(self.urlEntry)
        self.notebook.append_page(vbox, None)

        labelEnd = gtk.Label("Success")
        
        self.notebook.append_page(labelEnd, None)      

        hildon.WizardDialog.__init__(self, parent, "Add Feed", self.notebook)
   
        # Set a handler for "switch-page" signal
        #self.notebook.connect("switch_page", self.on_page_switch, self)
   
        # Set a function to decide if user can go to next page
        self.set_forward_page_func(self.some_page_func)
   
        self.show_all()
        
    def getData(self):
        return (self.nameEntry.get_text(), self.urlEntry.get_text())
        
    def on_page_switch(self, notebook, page, num, dialog):
        return True
   
    def some_page_func(self, nb, current, userdata):
        # Validate data for 1st page
        if current == 0:
            return len(self.nameEntry.get_text()) != 0
        elif current == 1:
            # Check the url is not null, and starts with http
            return ( (len(self.urlEntry.get_text()) != 0) and (self.urlEntry.get_text().lower().startswith("http")) )
        elif current != 2:
            return False
        else:
            return True

#class GetImage(threading.Thread):
#    def __init__(self, url, stream):
#        threading.Thread.__init__(self)
#        self.url = url
#        self.stream = stream
#    
#    def run(self):
#        f = urllib2.urlopen(self.url)
#        data = f.read()
#        f.close()
#        self.stream.write(data)
#        self.stream.close()
#
#class ImageDownloader():
#    def __init__(self):
#        self.images = []
#        self.downloading = False
#        
#    def queueImage(self, url, stream):
#        self.images.append((url, stream))
#        if not self.downloading:
#            self.downloading = True
#            gobject.timeout_add(50, self.checkQueue)
#        
#    def checkQueue(self):
#        for i in range(4-threading.activeCount()):
#            if len(self.images) > 0:
#                (url, stream) = self.images.pop() 
#                GetImage(url, stream).start()
#        if len(self.images)>0:
#            gobject.timeout_add(200, self.checkQueue)
#        else:
#            self.downloading=False
#            
#    def stopAll(self):
#        self.images = []
        
        
class Download(threading.Thread):
    def __init__(self, listing, key, config):
        threading.Thread.__init__(self)
        self.listing = listing
        self.key = key
        self.config = config
        
    def run (self):
        (use_proxy, proxy) = self.config.getProxy()
        if use_proxy:
            self.listing.updateFeed(self.key, self.config.getExpiry(), proxy=proxy, imageCache=self.config.getImageCache() )
        else:
            self.listing.updateFeed(self.key, self.config.getExpiry(), imageCache=self.config.getImageCache() )

        
class DownloadBar(gtk.ProgressBar):
    def __init__(self, parent, listing, listOfKeys, config, single=False):
        gtk.ProgressBar.__init__(self)
        self.listOfKeys = listOfKeys[:]
        self.listing = listing
        self.total = len(self.listOfKeys)
        self.config = config
        self.current = 0
        self.single = single
        
        if self.total>0:
            #self.progress = gtk.ProgressBar()
            #self.waitingWindow = hildon.Note("cancel", parent, "Downloading",
            #                     progressbar=self.progress)
            self.set_text("Updating...")
            self.fraction = 0
            self.set_fraction(self.fraction)
            self.show_all()
            # Create a timeout
            self.timeout_handler_id = gobject.timeout_add(50, self.update_progress_bar)
            #self.waitingWindow.show_all()
            #response = self.waitingWindow.run()
            #self.listOfKeys = []
            #while threading.activeCount() > 1:
                # Wait for current downloads to finish
            #    time.sleep(0.1)
            #self.waitingWindow.destroy()

    def update_progress_bar(self):
        #self.progress_bar.pulse()
        if threading.activeCount() < 4:
            x = threading.activeCount() - 1
            k = len(self.listOfKeys)
            fin = self.total - k - x
            fraction = float(fin)/float(self.total) + float(x)/(self.total*2.)
            #print x, k, fin, fraction
            self.set_fraction(fraction)

            if len(self.listOfKeys)>0:
                self.current = self.current+1
                key = self.listOfKeys.pop()
                if (not self.listing.getCurrentlyDisplayedFeed() == key) or (self.single == True):
                    # Check if the feed is being displayed
                    download = Download(self.listing, key, self.config)
                    download.start()
                return True
            elif threading.activeCount() > 1:
                return True
            else:
                #self.waitingWindow.destroy()
                #self.destroy()
                self.emit("download-done", "success")
                return False 
        return True
    
    
class SortList(gtk.Dialog):
    def __init__(self, parent, listing):
        gtk.Dialog.__init__(self, "Organizer",  parent)
        self.listing = listing
        
        self.vbox2 = gtk.VBox(False, 10)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Move Up")
        button.connect("clicked", self.buttonUp)
        self.vbox2.pack_start(button, expand=False, fill=False)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Move Down")
        button.connect("clicked", self.buttonDown)
        self.vbox2.pack_start(button, expand=False, fill=False)

        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Add Feed")
        button.connect("clicked", self.buttonAdd)
        self.vbox2.pack_start(button, expand=False, fill=False)

        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Edit Feed")
        button.connect("clicked", self.buttonEdit)
        self.vbox2.pack_start(button, expand=False, fill=False)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Delete")
        button.connect("clicked", self.buttonDelete)
        self.vbox2.pack_start(button, expand=False, fill=False)
        
        #button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        #button.set_label("Done")
        #button.connect("clicked", self.buttonDone)
        #self.vbox.pack_start(button)
        self.hbox2= gtk.HBox(False, 10)
        self.pannableArea = hildon.PannableArea()
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview = gtk.TreeView(self.treestore)
        self.hbox2.pack_start(self.pannableArea, expand=True)
        self.displayFeeds()
        self.hbox2.pack_end(self.vbox2, expand=False)
        self.set_default_size(-1, 600)
        self.vbox.pack_start(self.hbox2)
        
        self.show_all()
        #self.connect("destroy", self.buttonDone)
        
    def displayFeeds(self):
        self.treeview.destroy()
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview = gtk.TreeView()
        
        self.treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
        hildon.hildon_gtk_tree_view_set_ui_mode(self.treeview, gtk.HILDON_UI_MODE_EDIT)
        self.refreshList()
        self.treeview.append_column(gtk.TreeViewColumn('Feed Name', gtk.CellRendererText(), text = 0))

        self.pannableArea.add(self.treeview)

        #self.show_all()

    def refreshList(self, selected=None, offset=0):
        rect = self.treeview.get_visible_rect()
        y = rect.y+rect.height
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        for key in self.listing.getListOfFeeds():
            item = self.treestore.append([self.listing.getFeedTitle(key), key])
            if key == selected:
                selectedItem = item
        self.treeview.set_model(self.treestore)
        if not selected == None:
            self.treeview.get_selection().select_iter(selectedItem)
            self.treeview.scroll_to_cell(self.treeview.get_model().get_path(selectedItem))
        self.pannableArea.show_all()

    def getSelectedItem(self):
        (model, iter) = self.treeview.get_selection().get_selected()
        if not iter:
            return None
        return model.get_value(iter, 1)

    def findIndex(self, key):
        after = None
        before = None
        found = False
        for row in self.treestore:
            if found:
                return (before, row.iter)
            if key == list(row)[0]:
                found = True
            else:
                before = row.iter
        return (before, None)

    def buttonUp(self, button):
        key  = self.getSelectedItem()
        if not key == None:
            self.listing.moveUp(key)
            self.refreshList(key, -10)

    def buttonDown(self, button):
        key = self.getSelectedItem()
        if not key == None:
            self.listing.moveDown(key)
            self.refreshList(key, 10)

    def buttonDelete(self, button):
        key = self.getSelectedItem()
        if not key == None:
            self.listing.removeFeed(key)
        self.refreshList()

    def buttonEdit(self, button):
        key = self.getSelectedItem()
        if not key == None:
            wizard = AddWidgetWizard(self, self.listing.getFeedUrl(key), self.listing.getFeedTitle(key))
            ret = wizard.run()
            if ret == 2:
                (title, url) = wizard.getData()
                if (not title == '') and (not url == ''):
                    self.listing.editFeed(key, title, url)
            wizard.destroy()
        self.refreshList()

    def buttonDone(self, *args):
        self.destroy()
        
    def buttonAdd(self, button, urlIn="http://"):
        wizard = AddWidgetWizard(self, urlIn)
        ret = wizard.run()
        if ret == 2:
            (title, url) = wizard.getData()
            if (not title == '') and (not url == ''): 
               self.listing.addFeed(title, url)
        wizard.destroy()
        self.refreshList()
               

class DisplayArticle(hildon.StackableWindow):
    def __init__(self, feed, id, key, config, listing):
        hildon.StackableWindow.__init__(self)
        #self.imageDownloader = ImageDownloader()
        self.feed = feed
        self.listing=listing
        self.key = key
        self.id = id
        self.set_title(feed.getTitle(id))
        self.config = config
        
        # Init the article display
        #if self.config.getWebkitSupport():
        self.view = webkit.WebView()
            #self.view.set_editable(False)
        #else:
        #    import gtkhtml2
        #    self.view = gtkhtml2.View()
        #    self.document = gtkhtml2.Document()
        #    self.view.set_document(self.document)
        #    self.document.connect("link_clicked", self._signal_link_clicked)
        self.pannable_article = hildon.PannableArea()
        self.pannable_article.add(self.view)
        #self.pannable_article.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
        #self.gestureId = self.pannable_article.connect('horizontal-movement', self.gesture)

        #if self.config.getWebkitSupport():
        contentLink = self.feed.getContentLink(self.id)
        self.feed.setEntryRead(self.id)
        #if key=="ArchivedArticles":
        self.view.open("file://" + contentLink)
        self.view.connect("motion-notify-event", lambda w,ev: True)

        #else:
        #self.view.load_html_string(self.text, contentLink) # "text/html", "utf-8", self.link)
        self.view.set_zoom_level(float(config.getArtFontSize())/10.)
        #else:
        #    if not key == "ArchivedArticles":
                # Do not download images if the feed is "Archived Articles"
        #        self.document.connect("request-url", self._signal_request_url)
            
        #    self.document.clear()
        #    self.document.open_stream("text/html")
        #    self.document.write_stream(self.text)
        #    self.document.close_stream()
        
        menu = hildon.AppMenu()
        # Create a button and add it to the menu
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Allow Horizontal Scrolling")
        button.connect("clicked", self.horiz_scrolling_button)
        menu.append(button)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Open in Browser")
        button.connect("clicked", self._signal_link_clicked, self.feed.getExternalLink(self.id))
        menu.append(button)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Add to Archived Articles")
        button.connect("clicked", self.archive_button)
        menu.append(button)
        
        self.set_app_menu(menu)
        menu.show_all()
        
        #self.event_box = gtk.EventBox()
        #self.event_box.add(self.pannable_article)
        self.add(self.pannable_article)
        
        
        self.pannable_article.show_all()

        self.destroyId = self.connect("destroy", self.destroyWindow)
        
        self.view.connect("button_press_event", self.button_pressed)
        self.gestureId = self.view.connect("button_release_event", self.button_released)
        #self.timeout_handler_id = gobject.timeout_add(300, self.reloadArticle)

    def button_pressed(self, window, event):
        #print event.x, event.y
        self.coords = (event.x, event.y)
        
    def button_released(self, window, event):
        x = self.coords[0] - event.x
        y = self.coords[1] - event.y
        
        if (abs(y) < 30):
            if (x > 15):
                self.emit("article-previous", self.id)
            elif (x<-15):
                self.emit("article-next", self.id)   
        #print x, y
        #print "Released"

    #def gesture(self, widget, direction, startx, starty):
    #    if (direction == 3):
    #        self.emit("article-next", self.index)
    #    if (direction == 2):
    #        self.emit("article-previous", self.index)
        #print startx, starty
        #self.timeout_handler_id = gobject.timeout_add(200, self.destroyWindow)

    def destroyWindow(self, *args):
        self.disconnect(self.destroyId)
        self.emit("article-closed", self.id)
        #self.imageDownloader.stopAll()
        self.destroy()
        
    def horiz_scrolling_button(self, *widget):
        self.pannable_article.disconnect(self.gestureId)
        self.pannable_article.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
        
    def archive_button(self, *widget):
        # Call the listing.addArchivedArticle
        self.listing.addArchivedArticle(self.key, self.id)
        
    #def reloadArticle(self, *widget):
    #    if threading.activeCount() > 1:
            # Image thread are still running, come back in a bit
    #        return True
    #    else:
    #        for (stream, imageThread) in self.images:
    #            imageThread.join()
    #            stream.write(imageThread.data)
    #            stream.close()
    #        return False
    #    self.show_all()

    def _signal_link_clicked(self, object, link):
        bus = dbus.SessionBus()
        proxy = bus.get_object("com.nokia.osso_browser", "/com/nokia/osso_browser/request")
        iface = dbus.Interface(proxy, 'com.nokia.osso_browser')
        iface.open_new_window(link)

    #def _signal_request_url(self, object, url, stream):
        #print url
    #    self.imageDownloader.queueImage(url, stream)
        #imageThread = GetImage(url)
        #imageThread.start()
        #self.images.append((stream, imageThread))


class DisplayFeed(hildon.StackableWindow):
    def __init__(self, listing, feed, title, key, config):
        hildon.StackableWindow.__init__(self)
        self.listing = listing
        self.feed = feed
        self.feedTitle = title
        self.set_title(title)
        self.key=key
        self.config = config
        
        self.downloadDialog = False
        
        self.listing.setCurrentlyDisplayedFeed(self.key)
        
        self.disp = False
        
        menu = hildon.AppMenu()
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Update Feed")
        button.connect("clicked", self.button_update_clicked)
        menu.append(button)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Mark All As Read")
        button.connect("clicked", self.buttonReadAllClicked)
        menu.append(button)
        self.set_app_menu(menu)
        menu.show_all()
        
        self.displayFeed()
        
        self.connect("destroy", self.destroyWindow)
        
    def destroyWindow(self, *args):
        self.feed.saveUnread(CONFIGDIR)
        self.listing.updateUnread(self.key, self.feed.getNumberOfUnreadItems())
        self.emit("feed-closed", self.key)
        self.destroy()
        #gobject.idle_add(self.feed.saveFeed, CONFIGDIR)
        self.listing.closeCurrentlyDisplayedFeed()

    def displayFeed(self):
        self.vboxFeed = gtk.VBox(False, 10)
        self.pannableFeed = hildon.PannableArea()
        self.pannableFeed.add_with_viewport(self.vboxFeed)
        self.pannableFeed.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
        self.buttons = {}
        for id in self.feed.getIds():
            button = gtk.Button(self.feed.getTitle(id))
            button.set_alignment(0,0)
            label = button.child
            if self.feed.isEntryRead(id):
                #label.modify_font(pango.FontDescription("sans 16"))
                label.modify_font(pango.FontDescription(self.config.getReadFont()))
                label.modify_fg(gtk.STATE_NORMAL, read_color) # gtk.gdk.color_parse("white"))
            else:
                #print self.listing.getFont() + " bold"
                label.modify_font(pango.FontDescription(self.config.getUnreadFont()))
                label.modify_fg(gtk.STATE_NORMAL, unread_color)
            label.set_line_wrap(True)
            
            label.set_size_request(self.get_size()[0]-50, -1)
            button.connect("clicked", self.button_clicked, id)
            self.buttons[id] = button
            
            self.vboxFeed.pack_start(button, expand=False)

        self.add(self.pannableFeed)
        self.show_all()
        
    def clear(self):
        self.pannableFeed.destroy()
        #self.remove(self.pannableFeed)

    def button_clicked(self, button, index, previous=False, next=False):
        #newDisp = DisplayArticle(self.feedTitle, self.feed.getArticle(index), self.feed.getLink(index), index, self.key, self.listing, self.config)
        newDisp = DisplayArticle(self.feed, index, self.key, self.config, self.listing)
        stack = hildon.WindowStack.get_default()
        if previous:
            tmp = stack.peek()
            stack.pop_and_push(1, newDisp, tmp)
            newDisp.show()
            gobject.timeout_add(200, self.destroyArticle, tmp)
            #print "previous"
            self.disp = newDisp
        elif next:
            newDisp.show_all()
            if type(self.disp).__name__ == "DisplayArticle":
                gobject.timeout_add(200, self.destroyArticle, self.disp)
            self.disp = newDisp
        else:
            self.disp = newDisp
            self.disp.show_all()
        
        self.ids = []
        self.ids.append(self.disp.connect("article-closed", self.onArticleClosed))
        self.ids.append(self.disp.connect("article-next", self.nextArticle))
        self.ids.append(self.disp.connect("article-previous", self.previousArticle))

    def destroyArticle(self, handle):
        handle.destroyWindow()

    def nextArticle(self, object, index):
        label = self.buttons[index].child
        label.modify_font(pango.FontDescription(self.config.getReadFont()))
        label.modify_fg(gtk.STATE_NORMAL, read_color) #  gtk.gdk.color_parse("white"))
        id = self.feed.getNextId(index)
        self.button_clicked(object, id, next=True)

    def previousArticle(self, object, index):
        label = self.buttons[index].child
        label.modify_font(pango.FontDescription(self.config.getReadFont()))
        label.modify_fg(gtk.STATE_NORMAL, read_color) # gtk.gdk.color_parse("white"))
        id = self.feed.getPreviousId(index)
        self.button_clicked(object, id, previous=True)

    def onArticleClosed(self, object, index):
        label = self.buttons[index].child
        label.modify_font(pango.FontDescription(self.config.getReadFont()))
        label.modify_fg(gtk.STATE_NORMAL, read_color) # gtk.gdk.color_parse("white"))
        self.buttons[index].show()

    def button_update_clicked(self, button):
        #bar = DownloadBar(self, self.listing, [self.key,], self.config ) 
        if not type(self.downloadDialog).__name__=="DownloadBar":
            self.pannableFeed.destroy()
            self.vbox = gtk.VBox(False, 10)
            self.downloadDialog = DownloadBar(self.window, self.listing, [self.key,], self.config, single=True )
            self.downloadDialog.connect("download-done", self.onDownloadsDone)
            self.vbox.pack_start(self.downloadDialog, expand=False, fill=False)
            self.add(self.vbox)
            self.show_all()
            
    def onDownloadsDone(self, *widget):
        self.vbox.destroy()
        self.feed = self.listing.getFeed(self.key)
        self.displayFeed()
        
    def buttonReadAllClicked(self, button):
        for index in self.feed.getIds():
            self.feed.setEntryRead(index)
            label = self.buttons[index].child
            label.modify_font(pango.FontDescription(self.config.getReadFont()))
            label.modify_fg(gtk.STATE_NORMAL, read_color) # gtk.gdk.color_parse("white"))
            self.buttons[index].show()


class FeedingIt:
    def __init__(self):
        # Init the windows
        self.window = hildon.StackableWindow()
        self.window.set_title("FeedingIt")
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
        self.mainVbox = gtk.VBox(False,10)
        self.pannableListing = gtk.Label("Loading...")
        self.mainVbox.pack_start(self.pannableListing)
        self.window.add(self.mainVbox)
        self.window.show_all()
        self.config = Config(self.window, CONFIGDIR+"config.ini")
        gobject.idle_add(self.createWindow)
        
    def createWindow(self):
        self.listing = Listing(CONFIGDIR)
        
        self.downloadDialog = False
        self.orientation = FremantleRotation("FeedingIt", main_window=self.window, app=self)
        self.orientation.set_mode(self.config.getOrientation())
        
        menu = hildon.AppMenu()
        # Create a button and add it to the menu
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Update All Feeds")
        button.connect("clicked", self.button_update_clicked, "All")
        menu.append(button)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Mark All As Read")
        button.connect("clicked", self.button_markAll)
        menu.append(button)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Organize Feeds")
        button.connect("clicked", self.button_organize_clicked)
        menu.append(button)

        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Preferences")
        button.connect("clicked", self.button_preferences_clicked)
        menu.append(button)
       
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Import Feeds")
        button.connect("clicked", self.button_import_clicked)
        menu.append(button)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Export Feeds")
        button.connect("clicked", self.button_export_clicked)
        menu.append(button)
        
        self.window.set_app_menu(menu)
        menu.show_all()
        
        self.feedWindow = hildon.StackableWindow()
        self.articleWindow = hildon.StackableWindow()

        self.displayListing()
        self.autoupdate = False
        self.checkAutoUpdate()
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
        gobject.idle_add(self.enableDbus)
        
    def enableDbus(self):
        dbusHandler = ServerObject(self)

    def button_markAll(self, button):
        for key in self.listing.getListOfFeeds():
            feed = self.listing.getFeed(key)
            for id in feed.getIds():
                feed.setEntryRead(id)
            feed.saveUnread(CONFIGDIR)
            self.listing.updateUnread(key, feed.getNumberOfUnreadItems())
        self.refreshList()

    def button_export_clicked(self, button):
        opml = ExportOpmlData(self.window, self.listing)
        
    def button_import_clicked(self, button):
        opml = GetOpmlData(self.window)
        feeds = opml.getData()
        for (title, url) in feeds:
            self.listing.addFeed(title, url)
        self.displayListing()

    def addFeed(self, urlIn="http://"):
        wizard = AddWidgetWizard(self.window, urlIn)
        ret = wizard.run()
        if ret == 2:
            (title, url) = wizard.getData()
            if (not title == '') and (not url == ''): 
               self.listing.addFeed(title, url)
        wizard.destroy()
        self.displayListing()

    def button_organize_clicked(self, button):
        org = SortList(self.window, self.listing)
        org.run()
        org.destroy()
        self.listing.saveConfig()
        self.displayListing()
        
    def button_update_clicked(self, button, key):
        if not type(self.downloadDialog).__name__=="DownloadBar":
            self.downloadDialog = DownloadBar(self.window, self.listing, self.listing.getListOfFeeds(), self.config )
            self.downloadDialog.connect("download-done", self.onDownloadsDone)
            self.mainVbox.pack_end(self.downloadDialog, expand=False, fill=False)
            self.mainVbox.show_all()
        #self.displayListing()

    def onDownloadsDone(self, *widget):
        self.downloadDialog.destroy()
        self.downloadDialog = False
        #self.displayListing()
        self.refreshList()

    def button_preferences_clicked(self, button):
        dialog = self.config.createDialog()
        dialog.connect("destroy", self.prefsClosed)

    def show_confirmation_note(self, parent, title):
        note = hildon.Note("confirmation", parent, "Are you sure you want to delete " + title +"?")

        retcode = gtk.Dialog.run(note)
        note.destroy()
        
        if retcode == gtk.RESPONSE_OK:
            return True
        else:
            return False
        
    def displayListing(self):
        try:
            self.mainVbox.remove(self.pannableListing)
        except:
            pass
        self.vboxListing = gtk.VBox(False,10)
        self.pannableListing = hildon.PannableArea()
        self.pannableListing.add_with_viewport(self.vboxListing)

        self.buttons = {}
        list = self.listing.getListOfFeeds()[:]
        #list.reverse()
        for key in list:
            #button = gtk.Button(item)
            button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
                              hildon.BUTTON_ARRANGEMENT_VERTICAL)
            button.set_text(self.listing.getFeedTitle(key), self.listing.getFeedUpdateTime(key) + " / " 
                            + str(self.listing.getFeedNumberOfUnreadItems(key)) + " Unread Items")
            button.set_alignment(0,0,1,1)
            button.connect("clicked", self.buttonFeedClicked, self, self.window, key)
            self.vboxListing.pack_start(button, expand=False)
            self.buttons[key] = button
     
        self.mainVbox.pack_start(self.pannableListing)
        self.window.show_all()

    def refreshList(self):
        for key in self.listing.getListOfFeeds():
            if self.buttons.has_key(key):
                button = self.buttons[key]
                button.set_text(self.listing.getFeedTitle(key), self.listing.getFeedUpdateTime(key) + " / " 
                            + str(self.listing.getFeedNumberOfUnreadItems(key)) + " Unread Items")
            else:
                self.displayListing()
                break

    def buttonFeedClicked(widget, button, self, window, key):
        self.disp = DisplayFeed(self.listing, self.listing.getFeed(key), self.listing.getFeedTitle(key), key, self.config)
        self.disp.connect("feed-closed", self.onFeedClosed)

    def onFeedClosed(self, object, key):
        self.listing.saveConfig()
        self.refreshList()
     
    def run(self):
        self.window.connect("destroy", gtk.main_quit)
        gtk.main()
        self.listing.saveConfig()

    def prefsClosed(self, *widget):
        self.orientation.set_mode(self.config.getOrientation())
        self.checkAutoUpdate()

    def checkAutoUpdate(self, *widget):
        interval = int(self.config.getUpdateInterval()*3600000)
        if self.config.isAutoUpdateEnabled():
            if self.autoupdate == False:
                self.autoupdateId = gobject.timeout_add(interval, self.automaticUpdate)
                self.autoupdate = interval
            elif not self.autoupdate == interval:
                # If auto-update is enabled, but not at the right frequency
                gobject.source_remove(self.autoupdateId)
                self.autoupdateId = gobject.timeout_add(interval, self.automaticUpdate)
                self.autoupdate = interval
        else:
            if not self.autoupdate == False:
                gobject.source_remove(self.autoupdateId)
                self.autoupdate = False

    def automaticUpdate(self, *widget):
        # Need to check for internet connection
        # If no internet connection, try again in 10 minutes:
        # gobject.timeout_add(int(5*3600000), self.automaticUpdate)
        self.button_update_clicked(None, None)
        return True
    
    def getStatus(self):
        status = ""
        for key in self.listing.getListOfFeeds():
            if self.listing.getFeedNumberOfUnreadItems(key) > 0:
                status += self.listing.getFeedTitle(key) + ": \t" +  str(self.listing.getFeedNumberOfUnreadItems(key)) + " Unread Items\n"
        if status == "":
            status = "No unread items"
        return status

if __name__ == "__main__":
    gobject.signal_new("feed-closed", DisplayFeed, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.signal_new("article-closed", DisplayArticle, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.signal_new("article-next", DisplayArticle, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.signal_new("article-previous", DisplayArticle, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.signal_new("download-done", DownloadBar, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.threads_init()
    if not isdir(CONFIGDIR):
        try:
            mkdir(CONFIGDIR)
        except:
            print "Error: Can't create configuration directory"
            sys.exit(1)
    app = FeedingIt()
    app.run()
