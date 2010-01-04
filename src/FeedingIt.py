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
# Version     : 0.1.1
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
import sys   
import urllib2
import gobject
from portrait import FremantleRotation

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
        
    def getData(self):
        return (self.nameEntry.get_text(), self.urlEntry.get_text())
        
    def on_page_switch(self, notebook, page, num, dialog):
        return True
   
    def some_page_func(self, nb, current, userdata):
        # Validate data for 1st page
        if current == 0:
            entry = nb.get_nth_page(current)
            # Check the name is not null
            return len(entry.get_text()) != 0
        elif current == 1:
            entry = nb.get_nth_page(current)
            # Check the url is not null, and starts with http
            return ( (len(entry.get_text()) != 0) and (entry.get_text().lower().startswith("http")) )
        elif current != 2:
            return False
        else:
            return True

class DisplayArticle(hildon.StackableWindow):
    def __init__(self, title, text):
        hildon.StackableWindow.__init__(self)
        self.text = text
        self.set_title(title)

        # Init the article display    
        self.view = gtkhtml2.View()
        self.pannable_article = hildon.PannableArea()
        self.pannable_article.add(self.view)
        self.pannable_article.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
        self.document = gtkhtml2.Document()
        self.view.set_document(self.document)
        
        self.document.clear()
        self.document.open_stream("text/html")
        self.document.write_stream(self.text)
        self.document.close_stream()
        
        menu = hildon.AppMenu()
        # Create a button and add it to the menu
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Display Images")
        button.connect("clicked", self.reloadArticle)
        menu.append(button)
        self.set_app_menu(menu)
        menu.show_all()
        
        self.add(self.pannable_article)
        
        self.show_all()
        
        self.document.connect("link_clicked", self._signal_link_clicked)
        self.document.connect("request-url", self._signal_request_url)
        #self.document.connect("ReloadArticle", self.reloadArticle)
        self.connect("destroy", self.destroyWindow)
        
    def destroyWindow(self, *args):
        self.destroy()
        
    def reloadArticle(self, widget):
        self.document.open_stream("text/html")
        self.document.write_stream(self.text)
        self.document.close_stream()

    def _signal_link_clicked(self, object, link):
        webbrowser.open(link)

    def _signal_request_url(self, object, url, stream):
        f = urllib2.urlopen(url)
        stream.write(f.read())
        stream.close()


class DisplayFeed(hildon.StackableWindow):
    def __init__(self, feed, title):
        hildon.StackableWindow.__init__(self)
        self.feed = feed
        self.feedTitle = title
        self.set_title(title)
        
        menu = hildon.AppMenu()
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Update Feed")
        button.connect("clicked", self.button_update_clicked)
        menu.append(button)
        self.set_app_menu(menu)
        menu.show_all()
        
        self.displayFeed()
        
        self.connect("destroy", self.destroyWindow)
        
    def destroyWindow(self, *args):
        self.destroy()

    def displayFeed(self):
        self.vboxFeed = gtk.VBox(False, 10)
        self.pannableFeed = hildon.PannableArea()
        self.pannableFeed.add_with_viewport(self.vboxFeed)
        self.pannableFeed.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
        
        index = 0
        for item in self.feed.getEntries():
            button = gtk.Button(item["title"])
            button.set_alignment(0,0)
            label = button.child
            label.modify_font(pango.FontDescription("sans 18"))
            label.set_line_wrap(True)
            
            label.set_size_request(self.get_size()[0]-50, -1)
            button.connect("clicked", self.button_clicked, index)
            
            self.vboxFeed.pack_start(button, expand=False)           
            index=index+1

        self.add(self.pannableFeed)
        self.show_all()
        
    def clear(self):
        self.remove(self.pannableFeed)
        
    def button_clicked(self, button, index):
        disp = DisplayArticle(self.feedTitle, self.feed.getArticle(index))

    def button_update_clicked(self, button):
        self.listing.getFeed(key).updateFeed()
        self.clear()
        self.displayFeed(key)


class FeedingIt:
    def __init__(self):
        self.listing = Listing()
        
        # Init the windows
        self.window = hildon.StackableWindow()
        self.window.set_title("FeedingIt")
        FremantleRotation("FeedingIt", main_window=self.window)
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
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Delete Feed")
        button.connect("clicked", self.button_delete_clicked)
        menu.append(button)
        
        self.window.set_app_menu(menu)
        menu.show_all()
        
        self.feedWindow = hildon.StackableWindow()
        self.articleWindow = hildon.StackableWindow()

        self.displayListing() 
        
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
        #hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
        if key == "All":
            self.listing.updateFeeds()
        else:
            self.listing.getFeed(key).updateFeed()
            self.displayFeed(key)            
        self.displayListing()
        #hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)

    def button_delete_clicked(self, button):
        self.pickerDialog = hildon.PickerDialog(self.window)
        #HildonPickerDialog
        self.pickerDialog.set_selector(self.create_selector())
        self.pickerDialog.show_all()
        
    def create_selector(self):
        selector = hildon.TouchSelector(text=True)
        # Selection multiple
        #selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        self.mapping = {}
        selector.connect("changed", self.selection_changed)

        for key in self.listing.getListOfFeeds():
            title=self.listing.getFeedTitle(key)
            selector.append_text(title)
            self.mapping[title]=key

        return selector

    def selection_changed(self, widget, data):
        current_selection = widget.get_current_text()
        #print 'Current selection: %s' % current_selection
        #print "To Delete: %s" % self.mapping[current_selection]
        self.pickerDialog.destroy()
        if self.show_confirmation_note(self.window, current_selection):
            self.listing.removeFeed(self.mapping[current_selection])
        del self.mapping
        self.displayListing()

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
    
    def buttonFeedClicked(widget, button, self, window, key):
        disp = DisplayFeed(self.listing.getFeed(key), self.listing.getFeedTitle(key))
     
    def run(self):
        self.window.connect("destroy", gtk.main_quit)
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
