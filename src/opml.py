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
# Version     : 0.2.2
# Description : Simple RSS Reader
# ============================================================================

from xml.dom.minidom import parse, parseString
import urllib2
import gtk
import hildon
import gobject
import time
from os.path import isfile, dirname
import gobject

class ExportOpmlData():
    def __init__(self, parent, listing):
        fs = hildon.FileSystemModel()
        dialog = hildon.FileChooserDialog(parent, gtk.FILE_CHOOSER_ACTION_SAVE, fs)
                               #(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                #gtk.STOCK_SAVE, gtk.RESPONSE_OK))
                               #)
        #dialog = gobject.new(hildon.FileChooserDialog, \
        #            action=gtk.FILE_CHOOSER_ACTION_SAVE)
        #dialog.set_default_response(gtk.RESPONSE_OK)
        #dialog.set_property('autonaming',False)
        #dialog.set_property('show-files',True)
        dialog.set_current_folder('/home/user/MyDocs/')
        dialog.set_current_name('feedingit-export')
        dialog.set_extension('opml')
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:
                filename = dialog.get_filename()
                print filename
            #try:

                cont = True
                if isfile(filename):
                    note = "File already exists. Aborted"
                    confirm = hildon.Note ("confirmation", parent, "File already exists. Are you sure you want to overwrite it?", gtk.STOCK_DIALOG_WARNING )
                    confirm.set_button_texts ("Yes", "Cancel")
                    response = confirm.run()
                    confirm.destroy()
                    if response == gtk.RESPONSE_OK:
                        cont = True
                    else:
                        note = "Operation cancelled."
                        cont = False
                if cont:
                    file = open(filename, "w")
                    file.write(self.getOpmlText(listing))
                    file.close()
                    note = "Feeds exported to %s" %filename
            #except:
                note = "Failed to export feeds"
            
            #dialog.destroy()
            #dialog = hildon.Note ("information", parent, note , gtk.STOCK_DIALOG_INFO )
            #dialog.run()
            #dialog.destroy()
        elif response == gtk.RESPONSE_CANCEL:
            dialog.destroy()  

    def getOpmlText(self, listing):
        time_now = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
        opml_text = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
<head>
    <title>Feeding It Export</title>
</head>
<body>
"""
        for key in listing.getListOfFeeds():
            title = listing.getFeedTitle(key)
            url = listing.getFeedUrl(key)
            if not title == "Archived Articles": 
                opml_text += """\n\t\t<outline  type="rss" text="%s" title="%s" xmlUrl="%s"/>""" % (self.sanitize(title), self.sanitize(title), self.sanitize(url))
        opml_text += """\n</body>\n</opml>\n"""
        return opml_text
    
    def sanitize(self, text):
	from cgi import escape
        return escape(text).encode('ascii', 'xmlcharrefreplace')
        
        

class GetOpmlData():
    def __init__(self, parent):
        self.parent = parent
        dialog = hildon.Note ("confirmation", parent, "What type of OPML?", gtk.STOCK_DIALOG_WARNING )
        dialog.set_button_texts ("File", "URL")
        response = dialog.run()
        dialog.destroy()
    
        if response == gtk.RESPONSE_OK:
            # Choose a file
            self.data = self.askForFile()
        else:
            # Download a URL
            self.data = self.downloadFile()
            
    def getData(self):
        if not self.data == None:
               dialog = OpmlDialog(self.parent, self.data)
               response = dialog.run()
               if response == gtk.RESPONSE_ACCEPT:
                   items = dialog.getItems()
               else:
                   items = []
               dialog.destroy()
               return items
        return []

    def downloadFile(self):
        dlg = gtk.Dialog("Import OPML from web", self.parent, gtk.DIALOG_DESTROY_WITH_PARENT,
                     ('Import', gtk.RESPONSE_OK,
                      gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        hb = gtk.HBox(False, 5)
        hb.pack_start(gtk.Label('URL:'), expand=False)
        entry = hildon.Entry(0)
        entry.set_text("http://")
        entry.select_region(-1, -1)
        hb.pack_start(entry, expand=True)
        hb.show_all()
        dlg.vbox.pack_start(hb, False)

        resp = dlg.run()
        url = entry.get_text()
        dlg.destroy()
        if resp == gtk.RESPONSE_CANCEL:
            return None
        try:
            f = urllib2.urlopen(url)
            data = f.read()
            f.close()
        except:
            #Show error note
            return None
        return data

    def askForFile(self):
        #dialog = hildon.FileChooserDialog(self.parent,
        #                       gtk.FILE_CHOOSER_ACTION_OPEN)
        #dialog = gobject.new(hildon.FileChooserDialog, \
        #            action=gtk.FILE_CHOOSER_ACTION_OPEN)
        #dialog.set_default_response(gtk.RESPONSE_OK)
        fs = hildon.FileSystemModel()
        dialog = hildon.FileChooserDialog(self.parent, gtk.FILE_CHOOSER_ACTION_OPEN, fs)
        
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("OPML")
        filter.add_pattern("*.xml")
        filter.add_pattern("*.opml")
        dialog.add_filter(filter)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            file = open(dialog.get_filename())
            data = file.read()
            file.close()
            dialog.destroy()
            return data
        elif response == gtk.RESPONSE_CANCEL:
            dialog.destroy()
            return None


class OpmlDialog(gtk.Dialog):
    def parse(self, opmlData):
        self.feeds = []
        dom1 = parseString(opmlData)
	
        outlines = dom1.getElementsByTagName('outline')
        for outline in outlines:
            title = outline.getAttribute('text')
            url = outline.getAttribute('xmlUrl')
            if url == "":
                url = outline.getAttribute('htmlUrl')
            if not url == "":
                self.feeds.append( (title, url) )
	
    def getFeedLinks(self):
        return self.feeds
	
    def __init__(self, parent, opmlData):
        self.parse(opmlData)
        gtk.Dialog.__init__(self, "Select OPML Feeds",  parent, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        
        self.pannableArea = hildon.PannableArea()
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview = gtk.TreeView(self.treestore)

        self.displayFeeds()

        self.set_default_size(-1, 600)
        self.vbox.pack_start(self.pannableArea)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Select All")
        button.connect("clicked", self.button_select_all_clicked)
        self.action_area.pack_end(button)
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Unselect All")
        button.connect("clicked", self.button_select_none_clicked)
        self.action_area.pack_end(button)
        
        self.show_all()
        
    def button_select_all_clicked(self, button):
        self.treeview.get_selection().select_all()
        
    def button_select_none_clicked(self, button):
        self.treeview.get_selection().unselect_all()
        
    def displayFeeds(self):
        self.treeview.destroy()
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview = gtk.TreeView()
        
        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        hildon.hildon_gtk_tree_view_set_ui_mode(self.treeview, gtk.HILDON_UI_MODE_EDIT)
        self.refreshList()
        self.treeview.append_column(gtk.TreeViewColumn('Feed Name', gtk.CellRendererText(), text = 0))

        self.pannableArea.add(self.treeview)
        self.pannableArea.show_all()
        self.treeview.get_selection().select_all()

    def refreshList(self, selected=None, offset=0):
        rect = self.treeview.get_visible_rect()
        y = rect.y+rect.height
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview.set_model(self.treestore)
        for (title, url) in self.feeds:
            item = self.treestore.append([title, url])
            self.treeview.get_selection().select_iter(item)
        #self.treeview.get_selection().select_all()
        self.pannableArea.show_all()

    def getItems(self):
        list = []
        treeselection = self.treeview.get_selection()
        (model, pathlist) = treeselection.get_selected_rows()
        for path in pathlist:
            list.append( (model.get_value(model.get_iter(path),0), model.get_value(model.get_iter(path),1)) )
        return list

def showOpmlData(widget, parent, button):
    dialog = GetOpmlData(parent)
    print dialog.getData()
    #dialog.destroy()

if __name__ == "__main__":
    window = hildon.Window()
    window.set_title("Test App")

    
    button = gtk.Button("Click to confirm.")
    window.add(button)
    button.connect("clicked", showOpmlData, window, button)
    window.connect("destroy", gtk.main_quit)
    window.show_all()

    gtk.main()
    window.destroy()
