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

class OpmlDialog(gtk.Dialog):
    def parse(self, opmlData):
	self.feeds = []
	dom1 = parseString(self.opmlData)
	
	outlines = dom1.getElementsByTagName('outline')
	for outline in outlines:
	  title = outline.getAttribute('text')
	  url = outline.getAttribute('xmlUrl')
	  if url == "":
	    url = outline.getAttribute('htmlUrl')
	  self.feeds.append(title, url)
	
    def getFeedLinks(self):
	return self.feeds
	
    def __init__(self, parent, opmlData)
	self.parse(opmlData)
    
	gtk.Dialog.__init__(self, "Import OPML Feeds",  parent)
        
        self.vbox2 = gtk.VBox(False, 10)
        
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
        
    def displayFeeds(self):
        self.treeview.destroy()
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview = gtk.TreeView()
        
        self.treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
        hildon.hildon_gtk_tree_view_set_ui_mode(self.treeview, gtk.HILDON_UI_MODE_EDIT)
        self.refreshList()
        self.treeview.append_column(gtk.TreeViewColumn('Feed Name', gtk.CellRendererText(), text = 0))

        self.pannableArea.add(self.treeview)


    def refreshList(self, selected=None, offset=0):
        #x = self.treeview.get_visible_rect().x
        rect = self.treeview.get_visible_rect()
        y = rect.y+rect.height
        #self.pannableArea.jump_to(-1, 0)
        self.treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        for (title, url) in self.feeds():
            item = self.treestore.append([title, url])
	    self.treeview.get_selection().select_iter(item)
        self.treeview.set_model(self.treestore)
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

    def buttonDone(self, *args):
        self.destroy()



