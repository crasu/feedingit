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
#import sys
#sys.path.insert(0, '/opt/FeedingIt')
#sys.path.insert(0, '/home/user/workspace/feedingit/src/')

import gtk, pickle, gobject, dbus
import hildondesktop, hildon
#from rss import Listing

# Create a session bus.
import dbus
from dbus.mainloop.glib import DBusGMainLoop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()

CONFIGDIR="/home/user/.feedingit/"

class FeedingItHomePlugin(hildondesktop.HomePluginItem):
    def __init__(self):
      try:
        hildondesktop.HomePluginItem.__init__(self)
        self.set_settings(True)
        self.connect("show-settings", self.show_settings)
        self.feed_list = {}
        
        vbox = gtk.VBox(False, 0)
        
        button = gtk.Button("Update")
        button.connect("clicked", self.update_list)
        button.show_all()
        vbox.pack_start(button)        
        
        #for feed in ["Slashdot", "Engadget", "Cheez"]:
        #    self.treestore.append([feed, "0"])
        self.treeview = gtk.TreeView()
        self.update_list()
        self.treeview.append_column(gtk.TreeViewColumn('Feed Name', gtk.CellRendererText(), text = 0))
        self.treeview.append_column(gtk.TreeViewColumn('Unread Items', gtk.CellRendererText(), text = 1))
        #self.treeview.get_selection().set_mode(gtk.SELECTION_NONE)
        #hildon.hildon_gtk_tree_view_set_ui_mode(self.treeview, gtk.HILDON_UI_MODE_NORMAL)
        
        vbox.pack_start(self.treeview)
        
        self.add(vbox)
        self.treeview.connect("row-activated", self.row_activated)
        vbox.show_all()
        #self.setupDbus()
        gobject.timeout_add_seconds(30*60, self.update_list)
      except:
          import traceback
          file = open("/home/user/.feedingit/feedingit_widget.log", "w")
          traceback.print_exc(file=file)

    def row_activated(self, treeview, treepath, column):
        (model, iter) = self.treeview.get_selection().get_selected()
        key = model.get_value(iter, 2)
        # Create an object that will proxy for a particular remote object.
        remote_object = bus.get_object("org.maemo.feedingit", # Connection name
                               "/org/maemo/feedingit" # Object's path
                              )
        iface = dbus.Interface(remote_object, 'org.maemo.feedingit')
        iface.OpenFeed(key)

    def update_list(self, *widget):
        #listing = Listing(CONFIGDIR)
        treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        
        if self.feed_list == {}:
            self.load_config()

        list = []
        #for key in listOfFeeds["feedingit-order"]:
        for key in self.feed_list.keys():
            try:
                file = open(CONFIGDIR+key+".d/unread", "r")
                readItems = pickle.load( file )
                file.close()
                countUnread = 0
                for id in readItems.keys():
                    if readItems[id]==False:
                        countUnread = countUnread + 1
                list.append([self.feed_list[key], countUnread, key])
            except:
                pass
        list = sorted(list, key=lambda item: item[1], reverse=True)
        for item in list[0:8]:
            treestore.append(item)
        self.treeview.set_model(treestore)
        self.treeview.get_selection().unselect_all()
        return True
        
    def show_settings(self, widget):
        file = open(CONFIGDIR+"feeds.pickle")
        listOfFeeds = pickle.load(file)
        file.close()
        dialog = gtk.Dialog("Settings", None, gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_NO_SEPARATOR, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))

        self.pannableArea = hildon.PannableArea()
        
        #self.treestore_settings = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview_settings = gtk.TreeView()
        
        self.treeview_settings.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        hildon.hildon_gtk_tree_view_set_ui_mode(self.treeview_settings, gtk.HILDON_UI_MODE_EDIT)
        dialog.vbox.pack_start(self.pannableArea)
        
        self.treeview_settings.append_column(gtk.TreeViewColumn('Feed Name', gtk.CellRendererText(), text = 0))
        self.treestore_settings = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview_settings.set_model(self.treestore_settings)
        
        for key in listOfFeeds["feedingit-order"]:
            title = listOfFeeds[key]["title"]
            item = self.treestore_settings.append([title, key])
            if key in self.feed_list:
                self.treeview_settings.get_selection().select_iter(item)
            
        self.pannableArea.add(self.treeview_settings)
        self.pannableArea.show_all()
        dialog.set_default_size(-1, 600)
        dialog.show_all()
        response = dialog.run()
        print response
        if response == gtk.RESPONSE_ACCEPT:
            self.feed_list = self.getItems()
        dialog.destroy()
        self.update_list()
        #self.treeview_settings.get_selection().select_all()
        
    def getItems(self):
        list = {}
        treeselection = self.treeview_settings.get_selection()
        (model, pathlist) = treeselection.get_selected_rows()
        for path in pathlist:
            list[model.get_value(model.get_iter(path),1)] = model.get_value(model.get_iter(path),0)
        return list
        
    def setupDbus(self):
        
        #from dbus.mainloop.glib import DBusGMainLoop
        #dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        #import gobject
        #loop = gobject.MainLoop()
        #bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
        #bus = dbus.SessionBus(mainloop=loop)
        #bus = dbus.Bus.get_system()
        #bus = dbus.Bus.get_session(True)
        #bus.set_exit_on_disconnect(False)
        
        remote_object = bus.get_object("org.maemo.feedingit", # Connection name
                               "/org/maemo/feedingit" # Object's path
                              )
        iface = dbus.Interface(remote_object, 'org.maemo.feedingit')
        iface.connect_to_signal("ArticleCountUpdated", self.update_list)

        #bus.add_signal_receiver(self.update_list,
        #                dbus_interface="org.maemo.feedingit",
        #                signal_name="ArticleCountUpdated",
        #                path="/org/maemo/feedingit")
        
    def save_config(self):
            if not isdir(CONFIGDIR):
                mkdir(CONFIGDIR)
            file = open(CONFIGDIR+"widget", "w")
            pickle.dump(self.feed_list, file )
            file.close()
            
    def load_config(self):
            try:
                file = open(CONFIGDIR+"widget", "r")
                self.feed_list = pickle.load( file )
                file.close()
            except:
                file = open(CONFIGDIR+"feeds.pickle")
                listOfFeeds = pickle.load(file)
                file.close()
            
                #self.feed_list = listOfFeeds["feedingit-order"]
                for key in listOfFeeds["feedingit-order"]:
                    self.feed_list[key] = listOfFeeds[key]["title"]
                del listOfFeeds


hd_plugin_type = FeedingItHomePlugin

# The code below is just for testing purposes.
# It allows to run the widget as a standalone process.
if __name__ == "__main__":
    import gobject
    gobject.type_register(hd_plugin_type)
    obj = gobject.new(hd_plugin_type, plugin_id="plugin_id")
    obj.show_all()
    gtk.main()
