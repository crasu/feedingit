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

import sqlite3
from re import sub
from htmlentitydefs import name2codepoint

import gtk, pickle, gobject, dbus
import hildondesktop, hildon
from pango import ELLIPSIZE_END
#from rss import Listing

# Create a session bus.
import dbus
from dbus.mainloop.glib import DBusGMainLoop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
#bus = dbus.SessionBus()

from os import environ, remove
bus = dbus.bus.BusConnection(environ["DBUS_SESSION_BUS_ADDRESS"])
from os.path import isfile
from cgi import escape

settings = gtk.settings_get_default()
color_style = gtk.rc_get_style_by_paths( settings, 'GtkButton', 'osso-logical-colors', gtk.Button)
active_color = color_style.lookup_color('ActiveTextColor')
default_color = color_style.lookup_color('DefaultTextColor')
font_desc = gtk.rc_get_style_by_paths(settings, 'HomeSystemFont', None, None).font_desc

del color_style

CONFIGDIR="/home/user/.feedingit/"
SOURCE=CONFIGDIR + "source"

#DBusConnection *hd_home_plugin_item_get_dbus_connection ( HDHomePluginItem *item, DBusBusType type, DBusError *error);
#import ctypes
#libc = ctypes.CDLL('libc.so.6')
#libc.printf('Hello world!')

def get_font_desc(logicalfontname):
    settings = gtk.settings_get_default()
    font_style = gtk.rc_get_style_by_paths(settings, logicalfontname, \
            None, None)
    font_desc = font_style.font_desc
    return font_desc

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

def fix_title(title):
    return escape(unescape(title).replace("<em>","").replace("</em>","").replace("<nobr>","").replace("</nobr>","").replace("<wbr>",""))


class FeedingItHomePlugin(hildondesktop.HomePluginItem):
    def __init__(self):
      __gsignals__ = {
      'destroy' : 'override'
      }

      try:
        hildondesktop.HomePluginItem.__init__(self)
        self.set_settings(True)
        self.connect("show-settings", self.show_settings)
        self.initialized = False
        self.total = 0
        self.status = 0 # 0=Showing feeds, 1=showing articles
        self.updateStatus = 0 # 0=Not updating, 1=Update in progress
        self.pageStatus = 0
        self.pageSize = 10
        self.size = 1 # 1=Big widget, 0=small widget
        
        if isfile(SOURCE):
            file = open(SOURCE)
            self.autoupdateId = int(file.read())
            file.close() 
        else:
            self.autoupdateId=False
        self.load_config()
        
        vbox = gtk.VBox(False, 0)
        
        ## Prepare the main HBox
        self.hbox1 = gtk.HBox(False, 0)
        #self.button = gtk.Button()
        self.buttonApp = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        #self.buttonApp.set_text("FeedingIt","")
        #self.button.set_sensitive(False)
        #self.label1 = self.buttonApp.child.child.get_children()[0].get_children()[0]
        #self.label2 = self.button.child.child.get_children()[0].get_children()[1]
        #self.label1.modify_fg(gtk.STATE_INSENSITIVE, default_color)
        #self.label1.modify_font(font_desc)
        #self.label2.modify_fg(gtk.STATE_INSENSITIVE, active_color)
        icon_theme = gtk.icon_theme_get_default()
        pixbuf = icon_theme.load_icon("feedingit", 20, gtk.ICON_LOOKUP_USE_BUILTIN )
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        self.buttonApp.set_image(image)
        self.buttonApp.set_image_position(gtk.POS_RIGHT)
        #button = gtk.Button("Update")
        self.buttonApp.connect("clicked", self.button_clicked)
        
        self.buttonUpdate = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        self.buttonUpdate.set_image(gtk.image_new_from_icon_name('general_refresh', gtk.ICON_SIZE_BUTTON))
        self.buttonUpdate.connect("clicked", self.buttonUpdate_clicked)
        
        if self.size==1:
            self.buttonUp = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            self.buttonUp.set_image(gtk.image_new_from_icon_name('keyboard_move_up', gtk.ICON_SIZE_BUTTON))
            self.buttonUp.set_sensitive(False)
            self.buttonUp.connect("clicked", self.buttonUp_clicked)
            
            self.buttonDown = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            self.buttonDown.set_image(gtk.image_new_from_icon_name('keyboard_move_down', gtk.ICON_SIZE_BUTTON))
            self.buttonDown.set_sensitive(False)
            self.buttonDown.connect("clicked", self.buttonDown_clicked)
        
        self.hbox1.pack_start(self.buttonUpdate, expand=False)
        if self.size==1:
            self.hbox1.pack_start(self.buttonUp, expand=False)
            self.hbox1.pack_start(self.buttonDown, expand=False)
        self.hbox1.pack_start(self.buttonApp, expand=False)
        
        #button.show_all()
               
        
        #for feed in ["Slashdot", "Engadget", "Cheez"]:
        #    self.treestore.append([feed, "0"])
        self.treeview = gtk.TreeView()
        self.update_list()
        name_renderer = gtk.CellRendererText()
        name_renderer.set_property("font-desc", font_desc)
        name_renderer.set_property('background', "#333333")
        name_renderer.set_property('ellipsize', ELLIPSIZE_END)
        self.unread_renderer = gtk.CellRendererText()
        self.unread_renderer.set_property("font-desc", font_desc)
        self.unread_renderer.set_property("xalign", 1.0)
        self.unread_renderer.set_property('background', "#333333")
        column_unread = gtk.TreeViewColumn('Unread Items', self.unread_renderer, text = 1)
        column_unread.set_expand(False)
        column_name = gtk.TreeViewColumn('Feed Name', name_renderer, markup = 0)
        column_name.set_expand(True)
        self.treeview.append_column(column_name)
        self.treeview.append_column(column_unread)
        #selection = self.treeview.get_selection()
        #selection.set_mode(gtk.SELECTION_NONE)
        #self.treeview.get_selection().set_mode(gtk.SELECTION_NONE)
        #hildon.hildon_gtk_tree_view_set_ui_mode(self.treeview, gtk.HILDON_UI_MODE_NORMAL)
        
        vbox.pack_start(self.treeview)
        vbox.pack_start(self.hbox1, expand=False) 
        
        self.add(vbox)
        self.treeview.connect("hildon-row-tapped", self.row_activated)
        #self.treeview.connect("cursor-changed", self.cursor_changed)
        vbox.show_all()
        self.set_resize_mode(gtk.RESIZE_QUEUE)
        self.setupDbus()
        #gobject.timeout_add_seconds(30*60, self.update_list)
      except:
          import traceback
          file = open("/home/user/feedingit_widget.log", "a")
          traceback.print_exc(file=file)
          file.close()
          
    def do_destroy(self):
        #file = open("/home/user/.feedingit/feedingit_widget.log", "a")
        #file.write("Do_destroy: ")
        if (not self.autoupdateId==False):
            gobject.source_remove(self.autoupdateId)
            self.autoupdateId=False
            #file.write("Destroyed %s\n" %self.autoupdateId)
            remove(SOURCE)
        hildondesktop.HomePluginItem.do_destroy(self)
        #file.write("End destroy\n")
        #file.close()

    def button_clicked(self, *widget):
        #self.button.set_sensitive(False)
        #self.label1.modify_fg(gtk.STATE_NORMAL, default_color)
        #self.label2.modify_fg(gtk.STATE_NORMAL, active_color)
        #self.update_label("Stopping")
        if self.status == 0:
            remote_object = bus.get_object("org.maemo.feedingit", # Connection name
                                   "/org/maemo/feedingit" # Object's path
                                  )
            iface = dbus.Interface(remote_object, 'org.maemo.feedingit')
            iface.OpenFeed(None)
        else:
            self.status = 0
            self.pageStatus = 0
            if self.size == 1:
                self.buttonUp.set_sensitive(False)
                self.buttonDown.set_sensitive(False)
            self.treeview.append_column(gtk.TreeViewColumn('Unread Items', self.unread_renderer, text = 1))
            self.update_list()
        #iface.StopUpdate()
        
    def buttonUpdate_clicked(self, *widget):
        remote_object = bus.get_object("org.marcoz.feedingit", # Connection name
                        "/org/marcoz/feedingit/update" # Object's path
                        )
        iface = dbus.Interface(remote_object, 'org.marcoz.feedingit')
        if self.updateStatus == 0:
            iface.UpdateAll()
        else:
            iface.StopUpdate()
            
    def buttonUp_clicked(self, *widget):
        if self.pageStatus > 0:
            self.pageStatus -= 1
        self.show_articles()
        
    def buttonDown_clicked(self, *widget):
        self.pageStatus += 1
        self.show_articles()
        
    def update_label(self, value=None):
        if value != None:
            self.buttonApp.set_title(str(value))
        else:
            self.buttonApp.set_title("")

    #def row_activated(self, treeview, treepath): #, column):
    #    (model, iter) = self.treeview.get_selection().get_selected()
    #    key = model.get_value(iter, 2)
        # Create an object that will proxy for a particular remote object.
    #    remote_object = bus.get_object("org.maemo.feedingit", # Connection name
    #                           "/org/maemo/feedingit" # Object's path
    #                          )
    #    iface = dbus.Interface(remote_object, 'org.maemo.feedingit')
    #    iface.OpenFeed(key)
   
    def show_articles(self):
        db = sqlite3.connect(CONFIGDIR+self.key+".d/"+self.key+".db")
        count = db.execute("SELECT count(*) FROM feed WHERE read=0;").fetchone()[0]
        if count>0:
            maxPage = count/self.pageSize
            print maxPage
            if self.pageStatus > maxPage:
                self.pageStatus = maxPage
            print self.pageStatus
        rows = db.execute("SELECT id, title FROM feed WHERE read=0 ORDER BY date DESC LIMIT ? OFFSET ?;", (self.pageSize, self.pageStatus*self.pageSize,) )
        treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        for row in rows:
            #title = fix_title(row[1][0:32])
            title = fix_title(row[1])
            id = row[0]
            treestore.append((title, id))
        self.treeview.set_model(treestore)
    
    def row_activated(self, treeview, treepath):
        if self.status == 0:
            if self.size == 1:
                self.status = 1
                self.pageStatus = 0
                (model, iter) = self.treeview.get_selection().get_selected()
                self.key = model.get_value(iter, 2)
                treeviewcolumn = self.treeview.get_column(1)
                self.treeview.remove_column(treeviewcolumn)
                self.show_articles()
                self.buttonApp.set_image(gtk.image_new_from_icon_name('general_back', gtk.ICON_SIZE_BUTTON))
                self.buttonUp.set_sensitive(True)
                self.buttonDown.set_sensitive(True)
            else:
                (model, iter) = self.treeview.get_selection().get_selected()
                id = model.get_value(iter, 2)
                remote_object = bus.get_object("org.maemo.feedingit", # Connection name
                                   "/org/maemo/feedingit" # Object's path
                                  )
                iface = dbus.Interface(remote_object, 'org.maemo.feedingit')
                iface.OpenFeed(id)
        else:
            (model, iter) = self.treeview.get_selection().get_selected()
            id = model.get_value(iter, 1)
            # Create an object that will proxy for a particular remote object.
            remote_object = bus.get_object("org.maemo.feedingit", # Connection name
                                   "/org/maemo/feedingit" # Object's path
                                  )
            iface = dbus.Interface(remote_object, 'org.maemo.feedingit')
            iface.OpenArticle(self.key, id)

    def check_db(self, db):
        table = db.execute("SELECT sql FROM sqlite_master").fetchone()
        from string import find
        if find(table[0], "widget")==-1:
                db.execute("ALTER TABLE feeds ADD COLUMN widget int;")
                db.execute("UPDATE feeds SET widget=1;")
                db.commit()

    def no_feeds_available(self, treestore):
        treestore.append(["No feeds added yet", "", None])
        treestore.append(["Start Application", "", None])
        #self.update_label("No feeds added yet")
        self.treeview.set_model(treestore)

    def update_list(self, *widget):
        #listing = Listing(CONFIGDIR)
        try:
            if self.status == 0:
                treestore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
                
                #if self.feed_list == {}:
                if self.initialized == False:
                    self.load_config()
                try:
                    db = sqlite3.connect(CONFIGDIR+"feeds.db")
                except:
                    self.no_feeds_available(treestore)
                    return True
                try:
                    rows = db.execute("SELECT id, title, unread FROM feeds WHERE widget=1 ORDER BY unread DESC LIMIT 10;")
                except:
                    self.check_db(db)
                    rows = db.execute("SELECT id, title, unread FROM feeds WHERE widget=1 ORDER BY unread DESC LIMIT 10;")
                self.pageSize = 0
                for row in rows:
                    self.pageSize += 1
                    id = row[0]
                    countUnread = row[2]
                    name = row[1]
                    treestore.append([name, countUnread, id])
                self.treeview.set_model(treestore)
                self.buttonApp.set_image(gtk.image_new_from_icon_name('feedingit', gtk.ICON_SIZE_BUTTON))
            return True
        except:
          import traceback
          file = open("/home/user/feedingit_widget.log", "a")
          traceback.print_exc(file=file)
          file.close()

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
        if setting == "autoupdate":
            if tmp == "Disabled":
                self.autoupdate = 0
            else:
                self.autoupdate = tmp
        elif setting == "sizing":
            if tmp == "Large":
                self.size=1
            else:
                self.size=0
        #current_selection = selector.get_current_text()
        #if current_selection:
        #    self.config[setting] = current_selection
        #gobject.idle_add(self.updateButton, setting)
        #self.saveConfig()
        
    def create_autoupdate_picker(self):
            picker = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            selector = self.create_selector(["Disabled", 0.5, 1, 2, 4, 12, 24], "autoupdate")
            picker.set_selector(selector)
            picker.set_title("Frequency of updates from the widget")
            picker.set_text("Setup Feed Auto-updates","Update every %s hours" %str(self.autoupdate) )
            picker.set_name('HildonButton-finger')
            picker.set_alignment(0,0,1,1)
            #self.buttons[setting] = picker
            #vbox.pack_start(picker, expand=False)
            return picker
        
    def create_size_picker(self):
            picker = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            selector = self.create_selector(["Small", "Large"], "sizing")
            picker.set_selector(selector)
            picker.set_title("Default Size For The Widget")
            if self.size ==1:
                tmp = "Large"
            else:
                tmp = "Small"
            picker.set_text("Widget Size (requires restart)", tmp)
            picker.set_name('HildonButton-finger')
            picker.set_alignment(0,0,1,1)
            #self.buttons[setting] = picker
            #vbox.pack_start(picker, expand=False)
            return picker
        
    def show_settings(self, widget):
        if isfile(CONFIGDIR+"feeds.db"):
            db = sqlite3.connect(CONFIGDIR+"feeds.db")
            
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
            
            feeds = db.execute("SELECT title, id, widget FROM feeds;")
            
            for feed in feeds:
                # feed is (id, title)
                item = self.treestore_settings.append(feed[0:2])
                if feed[2]==1:
                    self.treeview_settings.get_selection().select_iter(item)
                
            self.pannableArea.add(self.treeview_settings)
            self.pannableArea.show_all()
            dialog.set_default_size(-1, 600)
            
            dialog.action_area.pack_start(self.create_autoupdate_picker())
            dialog.action_area.pack_start(self.create_size_picker())
            
            dialog.show_all()
            response = dialog.run()
    
            if response == gtk.RESPONSE_ACCEPT:
                self.getItems()
            dialog.destroy()
            self.save_config()
            self.update_list()
        else:
            dialog = gtk.Dialog("Please add feeds first", None, gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_NO_SEPARATOR, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
            label = gtk.Label("Please add feeds through the main application")
            dialog.vbox.pack_start(label)
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()
        #self.treeview_settings.get_selection().select_all()
        
    def getItems(self):
        list = {}
        treeselection = self.treeview_settings.get_selection()
        (model, pathlist) = treeselection.get_selected_rows()
        db = sqlite3.connect(CONFIGDIR+"feeds.db")
        db.execute("UPDATE feeds SET widget=0;")
        for path in pathlist:
            id = model.get_value(model.get_iter(path),1)
            db.execute("UPDATE feeds SET widget=1 WHERE id=?;", (id,) )
        db.commit()
            #title = model.get_value(model.get_iter(path),0)
            #list[model.get_value(model.get_iter(path),1)] = model.get_value(model.get_iter(path),0)
        #return list
        
    def setupDbus(self):
        bus.add_signal_receiver(self.update_list, dbus_interface="org.marcoz.feedingit",
                        signal_name="ArticleCountUpdated", path="/org/marcoz/feedingit/update")
        bus.add_signal_receiver(self.update_started, dbus_interface="org.marcoz.feedingit",
                        signal_name="UpdateStarted", path="/org/marcoz/feedingit/update")
        bus.add_signal_receiver(self.update_finished, dbus_interface="org.marcoz.feedingit",
                        signal_name="UpdateFinished", path="/org/marcoz/feedingit/update")

    def update_started(self, *widget):
        self.buttonUpdate.set_image(gtk.image_new_from_icon_name('general_stop', gtk.ICON_SIZE_BUTTON))
        self.updateStatus = 1

    def update_finished(self, *widget):
        self.updateStatus = 0
        self.buttonUpdate.set_image(gtk.image_new_from_icon_name('general_refresh', gtk.ICON_SIZE_BUTTON))
        
    def start_update(self):
        try:
            if self.autoupdate >0:
                #file = open("/home/user/.feedingit/feedingit_widget.log", "a")
                #from time import localtime, strftime
                #import os
                #file.write("Widget: pid:%s ppid:%s time:%s\n" % (os.getpid(), os.getppid(), strftime("%a, %d %b %Y %H:%M:%S +0000", localtime())))
                #file.close()
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
            file = open(CONFIGDIR+"widget2", "w")
            pickle.dump(self.size, file )
            pickle.dump(self.autoupdate, file)
            file.close()
            self.setup_autoupdate()

    def setup_autoupdate(self):
        if (float(self.autoupdate) > 0):
            if (not self.autoupdateId==False):
                #file = open("/home/user/.feedingit/feedingit_widget.log", "a")
                #file.write("Disabling %s\n" % self.autoupdateId)
                #file.close()
                gobject.source_remove(self.autoupdateId)
                remove(SOURCE)
            self.autoupdateId = gobject.timeout_add_seconds(int(float(self.autoupdate)*3600), self.start_update)
            file = open(SOURCE, "w")
            file.write(str(self.autoupdateId))
            file.close()
            #file = open("/home/user/.feedingit/feedingit_widget.log", "a")
            #file.write("Started %s\n" % self.autoupdateId)
            #file.close()
        else:
            if (not self.autoupdateId==False):
                gobject.source_remove(self.autoupdateId)
                self.autoupdateId=False
                remove(SOURCE)

    def load_config(self):
            if isfile(CONFIGDIR+"widget2"):
                file = open(CONFIGDIR+"widget2", "r")
                self.size = pickle.load( file )
                self.autoupdate = pickle.load( file )
                file.close()
                self.setup_autoupdate()
            elif isfile(CONFIGDIR+"widget"):
                file = open(CONFIGDIR+"widget", "r")
                feed_list = pickle.load( file )
                self.autoupdate = pickle.load( file )
                file.close()
                self.setup_autoupdate()
                self.size = 1
                self.save_config()
                remove(CONFIGDIR+"widget")
            else:
                #self.feed_list = None
                self.autoupdate = 0
                self.size = 1
            self.initialized = True


hd_plugin_type = FeedingItHomePlugin

# The code below is just for testing purposes.
# It allows to run the widget as a standalone process.
if __name__ == "__main__":
    import gobject
    gobject.type_register(hd_plugin_type)
    obj = gobject.new(hd_plugin_type, plugin_id="plugin_id")
    obj.show_all()
    gtk.main()
