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
__appname__ = 'FeedingIt'
__author__  = 'Yves Marcoz'
__version__ = '0.6.2'
__description__ = 'A simple RSS Reader for Maemo 5'
# ============================================================================

import gtk
from pango import FontDescription
import pango
import hildon
#import gtkhtml2
#try:
from webkit import WebView
#    has_webkit=True
#except:
#    import gtkhtml2
#    has_webkit=False
from os.path import isfile, isdir, exists
from os import mkdir, remove, stat
import gobject
from aboutdialog import HeAboutDialog
from portrait import FremantleRotation
from threading import Thread, activeCount
from feedingitdbus import ServerObject
from updatedbus import UpdateServerObject, get_lock
from config import Config
from cgi import escape

from rss import Listing
from opml import GetOpmlData, ExportOpmlData

from urllib2 import install_opener, build_opener

from socket import setdefaulttimeout
timeout = 5
setdefaulttimeout(timeout)
del timeout

LIST_ICON_SIZE = 32
LIST_ICON_BORDER = 10

USER_AGENT = 'Mozilla/5.0 (compatible; Maemo 5;) %s %s' % (__appname__, __version__)
ABOUT_ICON = 'feedingit'
ABOUT_COPYRIGHT = 'Copyright (c) 2010 %s' % __author__
ABOUT_WEBSITE = 'http://feedingit.marcoz.org/'
ABOUT_BUGTRACKER = 'https://garage.maemo.org/tracker/?group_id=1202'
ABOUT_DONATE = None # TODO: Create a donation page + add its URL here

color_style = gtk.rc_get_style_by_paths(gtk.settings_get_default() , 'GtkButton', 'osso-logical-colors', gtk.Button)
unread_color = color_style.lookup_color('ActiveTextColor')
read_color = color_style.lookup_color('DefaultTextColor')
del color_style

CONFIGDIR="/home/user/.feedingit/"
LOCK = CONFIGDIR + "update.lock"

from re import sub
from htmlentitydefs import name2codepoint

COLUMN_ICON, COLUMN_MARKUP, COLUMN_KEY = range(3)

FEED_COLUMN_MARKUP, FEED_COLUMN_KEY = range(2)

import style

MARKUP_TEMPLATE = '<span font_desc="%s" foreground="%s">%%s</span>'

# Build the markup template for the Maemo 5 text style
head_font = style.get_font_desc('SystemFont')
sub_font = style.get_font_desc('SmallSystemFont')

head_color = style.get_color('ButtonTextColor')
sub_color = style.get_color('DefaultTextColor')
active_color = style.get_color('ActiveTextColor')

head = MARKUP_TEMPLATE % (head_font.to_string(), head_color.to_string())
normal_sub = MARKUP_TEMPLATE % (sub_font.to_string(), sub_color.to_string())

active_head = MARKUP_TEMPLATE % (head_font.to_string(), active_color.to_string())
active_sub = MARKUP_TEMPLATE % (sub_font.to_string(), active_color.to_string())

FEED_TEMPLATE = '\n'.join((head, normal_sub))
FEED_TEMPLATE_UNREAD = '\n'.join((head, active_sub))

ENTRY_TEMPLATE = head
ENTRY_TEMPLATE_UNREAD = active_head

##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
# http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return sub("&#?\w+;", fixup, text)


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
        
class Download(Thread):
    def __init__(self, listing, key, config):
        Thread.__init__(self)
        self.listing = listing
        self.key = key
        self.config = config
        
    def run (self):
        (use_proxy, proxy) = self.config.getProxy()
        key_lock = get_lock(self.key)
        if key_lock != None:
            if use_proxy:
                self.listing.updateFeed(self.key, self.config.getExpiry(), proxy=proxy, imageCache=self.config.getImageCache() )
            else:
                self.listing.updateFeed(self.key, self.config.getExpiry(), imageCache=self.config.getImageCache() )
        del key_lock

        
class DownloadBar(gtk.ProgressBar):
    def __init__(self, parent, listing, listOfKeys, config, single=False):
        
        update_lock = get_lock("update_lock")
        if update_lock != None:
            gtk.ProgressBar.__init__(self)
            self.listOfKeys = listOfKeys[:]
            self.listing = listing
            self.total = len(self.listOfKeys)
            self.config = config
            self.current = 0
            self.single = single
            (use_proxy, proxy) = self.config.getProxy()
            if use_proxy:
                opener = build_opener(proxy)
                opener.addheaders = [('User-agent', USER_AGENT)]
                install_opener(opener)
            else:
                opener = build_opener()
                opener.addheaders = [('User-agent', USER_AGENT)]
                install_opener(opener)

            if self.total>0:
                self.set_text("Updating...")
                self.fraction = 0
                self.set_fraction(self.fraction)
                self.show_all()
                # Create a timeout
                self.timeout_handler_id = gobject.timeout_add(50, self.update_progress_bar)

    def update_progress_bar(self):
        #self.progress_bar.pulse()
        if activeCount() < 4:
            x = activeCount() - 1
            k = len(self.listOfKeys)
            fin = self.total - k - x
            fraction = float(fin)/float(self.total) + float(x)/(self.total*2.)
            #print x, k, fin, fraction
            self.set_fraction(fraction)

            if len(self.listOfKeys)>0:
                self.current = self.current+1
                key = self.listOfKeys.pop()
                #if self.single == True:
                    # Check if the feed is being displayed
                download = Download(self.listing, key, self.config)
                download.start()
                return True
            elif activeCount() > 1:
                return True
            else:
                #self.waitingWindow.destroy()
                #self.destroy()
                try:
                    del self.update_lock
                except:
                    pass
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
        #rect = self.treeview.get_visible_rect()
        #y = rect.y+rect.height
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
        #self.set_title(feed.getTitle(id))
        self.set_title(self.listing.getFeedTitle(key))
        self.config = config
        self.set_for_removal = False
        
        # Init the article display
        #if self.config.getWebkitSupport():
        self.view = WebView()
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
        if contentLink.startswith("/home/user/"):
            self.view.open("file://" + contentLink)
        else:
            self.view.load_html_string('This article has not been downloaded yet. Click <a href="%s">here</a> to view online.' % contentLink, contentLink)
        self.view.connect("motion-notify-event", lambda w,ev: True)
        self.view.connect('load-started', self.load_started)
        self.view.connect('load-finished', self.load_finished)

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
        
        if key == "ArchivedArticles":
            button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
            button.set_label("Remove from Archived Articles")
            button.connect("clicked", self.remove_archive_button)
        else:
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

    def load_started(self, *widget):
        hildon.hildon_gtk_window_set_progress_indicator(self, 1)
        
    def load_finished(self, *widget):
        hildon.hildon_gtk_window_set_progress_indicator(self, 0)

    def button_pressed(self, window, event):
        #print event.x, event.y
        self.coords = (event.x, event.y)
        
    def button_released(self, window, event):
        x = self.coords[0] - event.x
        y = self.coords[1] - event.y
        
        if (2*abs(y) < abs(x)):
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
        if self.set_for_removal:
            self.emit("article-deleted", self.id)
        else:
            self.emit("article-closed", self.id)
        #self.imageDownloader.stopAll()
        self.destroy()
        
    def horiz_scrolling_button(self, *widget):
        self.pannable_article.disconnect(self.gestureId)
        self.pannable_article.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
        
    def archive_button(self, *widget):
        # Call the listing.addArchivedArticle
        self.listing.addArchivedArticle(self.key, self.id)
        
    def remove_archive_button(self, *widget):
        self.set_for_removal = True
        
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
        import dbus
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
    def __init__(self, listing, feed, title, key, config, updateDbusHandler):
        hildon.StackableWindow.__init__(self)
        self.listing = listing
        self.feed = feed
        self.feedTitle = title
        self.set_title(title)
        self.key=key
        self.config = config
        self.updateDbusHandler = updateDbusHandler
        
        self.downloadDialog = False
        
        #self.listing.setCurrentlyDisplayedFeed(self.key)
        
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
        
        if key=="ArchivedArticles":
            button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
            button.set_label("Purge Read Articles")
            button.connect("clicked", self.buttonPurgeArticles)
            menu.append(button)
        
        self.set_app_menu(menu)
        menu.show_all()
        
        self.displayFeed()
        
        self.connect('configure-event', self.on_configure_event)
        self.connect("destroy", self.destroyWindow)

    def on_configure_event(self, window, event):
        if getattr(self, 'markup_renderer', None) is None:
            return

        # Fix up the column width for wrapping the text when the window is
        # resized (i.e. orientation changed)
        self.markup_renderer.set_property('wrap-width', event.width-10)

    def destroyWindow(self, *args):
        #self.feed.saveUnread(CONFIGDIR)
        gobject.idle_add(self.feed.saveUnread, CONFIGDIR)
        self.listing.updateUnread(self.key, self.feed.getNumberOfUnreadItems())
        self.emit("feed-closed", self.key)
        self.destroy()
        #gobject.idle_add(self.feed.saveFeed, CONFIGDIR)
        #self.listing.closeCurrentlyDisplayedFeed()

    def fix_title(self, title):
        return escape(unescape(title).replace("<em>","").replace("</em>","").replace("<nobr>","").replace("</nobr>","").replace("<wbr>",""))

    def displayFeed(self):
        self.pannableFeed = hildon.PannableArea()

        self.pannableFeed.set_property('hscrollbar-policy', gtk.POLICY_NEVER)

        self.feedItems = gtk.ListStore(str, str)
        self.feedList = gtk.TreeView(self.feedItems)
        self.feedList.connect('row-activated', self.on_feedList_row_activated)
        self.pannableFeed.add(self.feedList)

        self.markup_renderer = gtk.CellRendererText()
        self.markup_renderer.set_property('wrap-mode', pango.WRAP_WORD_CHAR)
        self.markup_renderer.set_property('wrap-width', 780)
        markup_column = gtk.TreeViewColumn('', self.markup_renderer, \
                markup=FEED_COLUMN_MARKUP)
        self.feedList.append_column(markup_column)

        #self.pannableFeed.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)

        for id in self.feed.getIds():
            if not ( self.feed.isEntryRead(id) and self.config.getHideReadArticles() ):
                #title = self.feed.getTitle(id)
                title = self.fix_title(self.feed.getTitle(id))
    
                if self.feed.isEntryRead(id):
                    markup = ENTRY_TEMPLATE % title
                else:
                    markup = ENTRY_TEMPLATE_UNREAD % title
    
                self.feedItems.append((markup, id))

        self.add(self.pannableFeed)
        self.show_all()

    def clear(self):
        self.pannableFeed.destroy()
        #self.remove(self.pannableFeed)

    def on_feedList_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        key = model.get_value(iter, FEED_COLUMN_KEY)
        # Emulate legacy "button_clicked" call via treeview
        self.button_clicked(treeview, key)

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
        if self.key == "ArchivedArticles":
            self.ids.append(self.disp.connect("article-deleted", self.onArticleDeleted))
        self.ids.append(self.disp.connect("article-closed", self.onArticleClosed))
        self.ids.append(self.disp.connect("article-next", self.nextArticle))
        self.ids.append(self.disp.connect("article-previous", self.previousArticle))

    def buttonPurgeArticles(self, *widget):
        self.clear()
        self.feed.purgeReadArticles()
        self.feed.saveUnread(CONFIGDIR)
        self.feed.saveFeed(CONFIGDIR)
        self.displayFeed()

    def destroyArticle(self, handle):
        handle.destroyWindow()

    def mark_item_read(self, key):
        it = self.feedItems.get_iter_first()
        while it is not None:
            k = self.feedItems.get_value(it, FEED_COLUMN_KEY)
            if k == key:
                title = self.fix_title(self.feed.getTitle(key))
                markup = ENTRY_TEMPLATE % title
                self.feedItems.set_value(it, FEED_COLUMN_MARKUP, markup)
                break
            it = self.feedItems.iter_next(it)

    def nextArticle(self, object, index):
        self.mark_item_read(index)
        id = self.feed.getNextId(index)
        self.button_clicked(object, id, next=True)

    def previousArticle(self, object, index):
        self.mark_item_read(index)
        id = self.feed.getPreviousId(index)
        self.button_clicked(object, id, previous=True)

    def onArticleClosed(self, object, index):
        self.mark_item_read(index)

    def onArticleDeleted(self, object, index):
        self.clear()
        self.feed.removeArticle(index)
        self.feed.saveUnread(CONFIGDIR)
        self.feed.saveFeed(CONFIGDIR)
        self.displayFeed()

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
        self.updateDbusHandler.ArticleCountUpdated()
        
    def buttonReadAllClicked(self, button):
        for index in self.feed.getIds():
            self.feed.setEntryRead(index)
            self.mark_item_read(index)


class FeedingIt:
    def __init__(self):
        # Init the windows
        self.window = hildon.StackableWindow()
        self.window.set_title(__appname__)
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
        self.mainVbox = gtk.VBox(False,10)

        self.pannableListing = hildon.PannableArea()
        self.mainVbox.pack_start(self.pannableListing)

        self.feedItems = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        self.feedList = gtk.TreeView(self.feedItems)
        self.feedList.connect('row-activated', self.on_feedList_row_activated)
        self.pannableListing.add(self.feedList)

        icon_renderer = gtk.CellRendererPixbuf()
        icon_renderer.set_property('width', LIST_ICON_SIZE + 2*LIST_ICON_BORDER)
        icon_column = gtk.TreeViewColumn('', icon_renderer, \
                pixbuf=COLUMN_ICON)
        self.feedList.append_column(icon_column)

        markup_renderer = gtk.CellRendererText()
        markup_column = gtk.TreeViewColumn('', markup_renderer, \
                markup=COLUMN_MARKUP)
        self.feedList.append_column(markup_column)

        self.window.add(self.mainVbox)
        self.window.show_all()
        self.config = Config(self.window, CONFIGDIR+"config.ini")
        gobject.idle_add(self.createWindow)
        
    def createWindow(self):
        self.app_lock = get_lock("app_lock")
        if self.app_lock == None:
            self.pannableListing.set_label("Update in progress, please wait.")
            gobject.timeout_add_seconds(3, self.createWindow)
            return False
        self.listing = Listing(CONFIGDIR)
        
        self.downloadDialog = False
        self.orientation = FremantleRotation(__appname__, main_window=self.window, app=self)
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

        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("About")
        button.connect("clicked", self.button_about_clicked)
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
        self.dbusHandler = ServerObject(self)
        self.updateDbusHandler = UpdateServerObject(self)

    def button_markAll(self, button):
        for key in self.listing.getListOfFeeds():
            feed = self.listing.getFeed(key)
            for id in feed.getIds():
                feed.setEntryRead(id)
            feed.saveUnread(CONFIGDIR)
            self.listing.updateUnread(key, feed.getNumberOfUnreadItems())
        self.displayListing()

    def button_about_clicked(self, button):
        HeAboutDialog.present(self.window, \
                __appname__, \
                ABOUT_ICON, \
                __version__, \
                __description__, \
                ABOUT_COPYRIGHT, \
                ABOUT_WEBSITE, \
                ABOUT_BUGTRACKER, \
                ABOUT_DONATE)

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
            self.updateDbusHandler.UpdateStarted()
            self.downloadDialog = DownloadBar(self.window, self.listing, self.listing.getListOfFeeds(), self.config )
            self.downloadDialog.connect("download-done", self.onDownloadsDone)
            self.mainVbox.pack_end(self.downloadDialog, expand=False, fill=False)
            self.mainVbox.show_all()
        #self.displayListing()

    def onDownloadsDone(self, *widget):
        self.downloadDialog.destroy()
        self.downloadDialog = False
        self.displayListing()
        self.updateDbusHandler.UpdateFinished()
        self.updateDbusHandler.ArticleCountUpdated()

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
        icon_theme = gtk.icon_theme_get_default()
        default_pixbuf = icon_theme.load_icon(ABOUT_ICON, LIST_ICON_SIZE, \
                gtk.ICON_LOOKUP_USE_BUILTIN)

        self.feedItems.clear()
        for key in self.listing.getListOfFeeds():
            unreadItems = self.listing.getFeedNumberOfUnreadItems(key)
            if unreadItems > 0 or not self.config.getHideReadFeeds():
                title = self.listing.getFeedTitle(key)
                updateTime = self.listing.getFeedUpdateTime(key)
                
                subtitle = '%s / %d unread items' % (updateTime, unreadItems)
    
                if unreadItems:
                    markup = FEED_TEMPLATE_UNREAD % (title, subtitle)
                else:
                    markup = FEED_TEMPLATE % (title, subtitle)
    
                try:
                    icon_filename = self.listing.getFavicon(key)
                    pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(icon_filename, \
                            LIST_ICON_SIZE, LIST_ICON_SIZE)
                except:
                    pixbuf = default_pixbuf
    
                self.feedItems.append((pixbuf, markup, key))

    def on_feedList_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        key = model.get_value(iter, COLUMN_KEY)

        try:
            self.feed_lock
        except:
            # If feed_lock doesn't exist, we can open the feed, else we do nothing
            self.feed_lock = get_lock(key)
            self.disp = DisplayFeed(self.listing, self.listing.getFeed(key), \
                    self.listing.getFeedTitle(key), key, \
                    self.config, self.updateDbusHandler)
            self.disp.connect("feed-closed", self.onFeedClosed)

    def onFeedClosed(self, object, key):
        #self.listing.saveConfig()
        #del self.feed_lock
        gobject.idle_add(self.onFeedClosedTimeout)
        self.displayListing()
        #self.updateDbusHandler.ArticleCountUpdated()
        
    def onFeedClosedTimeout(self):
        self.listing.saveConfig()
        del self.feed_lock
        self.updateDbusHandler.ArticleCountUpdated()
     
    def run(self):
        self.window.connect("destroy", gtk.main_quit)
        gtk.main()
        self.listing.saveConfig()
        del self.app_lock

    def prefsClosed(self, *widget):
        self.orientation.set_mode(self.config.getOrientation())
        self.displayListing()
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
        #file = open("/home/user/.feedingit/feedingit_widget.log", "a")
        #from time import localtime, strftime
        #file.write("App: %s\n" % strftime("%a, %d %b %Y %H:%M:%S +0000", localtime()))
        #file.close()
        self.button_update_clicked(None, None)
        return True
    
    def stopUpdate(self):
        # Not implemented in the app (see update_feeds.py)
        try:
            self.downloadDialog.listOfKeys = []
        except:
            pass
    
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
    gobject.signal_new("article-deleted", DisplayArticle, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.signal_new("article-next", DisplayArticle, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.signal_new("article-previous", DisplayArticle, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.signal_new("download-done", DownloadBar, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    gobject.threads_init()
    if not isdir(CONFIGDIR):
        try:
            mkdir(CONFIGDIR)
        except:
            print "Error: Can't create configuration directory"
            from sys import exit
            exit(1)
    app = FeedingIt()
    app.run()
