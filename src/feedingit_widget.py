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
# Version     : 0.6.0
# Description : Simple RSS Reader
# ============================================================================
#import sys

import gtk, pickle, gobject, dbus
import hildondesktop, hildon
#from rss import Listing

# Create a session bus.
import dbus
from dbus.mainloop.glib import DBusGMainLoop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
#bus = dbus.SessionBus()

from os import environ
bus = dbus.bus.BusConnection(environ["DBUS_SESSION_BUS_ADDRESS"])

color_style = gtk.rc_get_style_by_paths(gtk.settings_get_default() , 'GtkButton', 'osso-logical-colors', gtk.Button)
active_color = color_style.lookup_color('ActiveTextColor')
default_color = color_style.lookup_color('DefaultTextColor')
del color_style

CONFIGDIR="/home/user/.feedingit/"

#DBusConnection *hd_home_plugin_item_get_dbus_connection ( HDHomePluginItem *item, DBusBusType type, DBusError *error);
#import ctypes
#libc = ctypes.CDLL('libc.so.6')
#libc.printf('Hello world!')

class FeedingItHomePlugin(hildondesktop.HomePluginItem):
    def __init__(self):
      try:
        hildondesktop.HomePluginItem.__init__(self)
        self.set_settings(True)
        self.connect("show-settings", self.show_settings)
        self.feed_list = {}
        self.total = 0
        self.autoupdateID=False
        
        vbox = gtk.VBox(False, 0)
        
        #self.button = gtk.Button()
        self.button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        self.button.set_text("FeedingIt","")
        self.button.set_sensitive(False)
        self.label1 = self.button.child.child.get_children()[0].get_children()[0]
        self.label2 = self.button.child.child.get_children()[0].get_children()[1]
        self.label1.modify_fg(gtk.STATE_INSENSITIVE, default_color)
        self.label2.modify_fg(gtk.STATE_INSENSITIVE, active_color)
        icon_theme = gtk.icon_theme_get_default()
        pixbuf = icon_theme.load_icon("feedingit", 48, gtk.ICON_LOOKUP_USE_BUILTIN )
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        self.button.set_image(image)
        self.button.set_image_position(gtk.POS_LEFT)

        #button = gtk.Button("Update")
        self.button.connect("clicked", self.button_clicked)
        #button.show_all()
        vbox.pack_start(self.button, expand=False)        
        
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
        self.setupDbus()
        #gobject.timeout_add_seconds(30*60, self.update_list)
      except:
          import traceback
          file = open("/home/user/.feedingit/feedingit_widget.log", "a")
          traceback.print_exc(file=file)
          file.close()

    def button_clicked(self, *widget):
        self.button.set_sensitive(False)
        self.label1.modify_fg(gtk.STATE_NORMAL, default_color)
        self.label2.modify_fg(gtk.STATE_NORMAL, active_color)
        self.update_label("Stopping")
        remote_object = bus.get_object("org.marcoz.feedingit", # Connection name
                               "/org/marcoz/feedingit/update" # Object's path
                              )
        iface = dbus.Interface(remote_object, 'org.marcoz.feedingit')
        iface.StopUpdate()
        
    def update_label(self, title, value=None):
        self.button.set_title(title)
        if value != None:
            self.button.set_value(value)
        else:
            self.button.set_value("")

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
        oldtotal = self.total
        self.total = 0
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
                self.total += countUnread
            except:
                pass
        list = sorted(list, key=lambda item: item[1], reverse=True)
        for item in list[0:8]:
            treestore.append(item)
        self.treeview.set_model(treestore)
        self.treeview.get_selection().unselect_all()
        if self.total > oldtotal:
            self.update_label("%s Unread" %str(self.total), "%s more articles" %str(self.total-oldtotal))
        else:
            self.update_label("%s Unread" %str(self.total))
        return True

    def create_selector(self, choices, setting):
        #self.pickerDialog = hildon.PickerDialog(self.parent)
        selector = hildon.TouchSelector(text=True)
        index = 0
        for item in choices:
            iter = selector.append_text(str(item))
            if str(self.autoupdate) == str(item): 
                selector.set_active(0, index)
            index += 1
        selector.connect("changed", self.selection_changed, setting)
        #self.pickerDialog.set_selector(selector)
        return selector
        
    def selection_changed(self, selector, button, setting):
        tmp = selector.get_current_text()
        if tmp == "Disabled":
            self.autoupdate = 0
        else:
            self.autoupdate = tmp
        #current_selection = selector.get_current_text()
        #if current_selection:
        #    self.config[setting] = current_selection
        #gobject.idle_add(self.updateButton, setting)
        #self.saveConfig()
        
    def create_autoupdate_picker(self):
            picker = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            selector = self.create_selector(["Disabled", 0.02, 0.5, 1, 2, 4, 12, 24], "autoupdate")
            picker.set_selector(selector)
            picker.set_title("Frequency of updates from the widget")
            picker.set_text("Setup Feed Auto-updates","Update every %s hours" %str(self.autoupdate) )
            picker.set_name('HildonButton-finger')
            picker.set_alignment(0,0,1,1)
            #self.buttons[setting] = picker
            #vbox.pack_start(picker, expand=False)
            return picker
        
    def show_settings(self, widget):
        file = open(CONFIGDIR+"feeds.pickle")
        listOfFeeds = pickle.load(file)
        file.close()
        dialog = gtk.Dialog("Choose feeds to display", None, gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_NO_SEPARATOR, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))

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
        
        dialog.action_area.pack_start(self.create_autoupdate_picker())
        
        dialog.show_all()
        response = dialog.run()

        if response == gtk.RESPONSE_ACCEPT:
            self.feed_list = self.getItems()
        dialog.destroy()
        self.save_config()
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
        bus.add_signal_receiver(self.update_list, dbus_interface="org.marcoz.feedingit",
                        signal_name="ArticleCountUpdated", path="/org/marcoz/feedingit/update")
        bus.add_signal_receiver(self.update_started, dbus_interface="org.marcoz.feedingit",
                        signal_name="UpdateStarted", path="/org/marcoz/feedingit/update")
        bus.add_signal_receiver(self.update_finished, dbus_interface="org.marcoz.feedingit",
                        signal_name="UpdateFinished", path="/org/marcoz/feedingit/update")

    def update_started(self, *widget):
        self.button.set_sensitive(True)
        self.update_label("Updating...", "Click to stop update")

    def update_finished(self, *widget):
        self.button.set_sensitive(False)
        self.update_label("Update done")
        
    def start_update(self):
        try:
            if self.autoupdate >0:
                import traceback
                file = open("/home/user/.feedingit/feedingit_widget.log", "a")
                from time import gmtime, strftime
                file.write(strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()))
                file.close()
                remote_object = bus.get_object("org.marcoz.feedingit", # Connection name
                              "/org/marcoz/feedingit/update" # Object's path
                              )
                iface = dbus.Interface(remote_object, 'org.marcoz.feedingit')
                iface.UpdateAll()
            return True
        except:
            import traceback
            file = open("/home/user/.feedingit/feedingit_widget.log", "a")
            traceback.print_exc(file=file)
            file.close()

    def save_config(self):
            from os.path import isdir
            if not isdir(CONFIGDIR):
                from os import mkdir
                mkdir(CONFIGDIR)
            file = open(CONFIGDIR+"widget", "w")
            pickle.dump(self.feed_list, file )
            pickle.dump(self.autoupdate, file)
            file.close()
            self.setup_autoupdate()

    def setup_autoupdate(self):
        if (float(self.autoupdate) > 0):
            if (not self.autoupdateID==False):
                gobject.disconnect(self.autoupdateId)
            self.autoupdateId = gobject.timeout_add_seconds(int(float(self.autoupdate)*3600), self.start_update)
        else:
            if (not self.autoupdateID==False):
                gobject.disconnect(self.autoupdateId)
                self.autoupdateID=False

    def load_config(self):
            try:
                file = open(CONFIGDIR+"widget", "r")
                self.feed_list = pickle.load( file )
                self.autoupdate = pickle.load( file )
                file.close()
                self.setup_autoupdate()
            except:
                file = open(CONFIGDIR+"feeds.pickle")
                listOfFeeds = pickle.load(file)
                file.close()
            
                #self.feed_list = listOfFeeds["feedingit-order"]
                for key in listOfFeeds["feedingit-order"]:
                    self.feed_list[key] = listOfFeeds[key]["title"]
                del listOfFeeds
                self.autoupdate = 0


hd_plugin_type = FeedingItHomePlugin

# The code below is just for testing purposes.
# It allows to run the widget as a standalone process.
if __name__ == "__main__":
    import gobject
    gobject.type_register(hd_plugin_type)
    obj = gobject.new(hd_plugin_type, plugin_id="plugin_id")
    obj.show_all()
    gtk.main()
