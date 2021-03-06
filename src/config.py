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
# Version     : 0.6.1
# Description : Simple RSS Reader
# ============================================================================

import gtk
import hildon
from ConfigParser import RawConfigParser
from gobject import idle_add
from gconf import client_get_default
from urllib2 import ProxyHandler

VERSION = "52"

section = "FeedingIt"
ranges = { "updateInterval":[0.5, 1, 2, 4, 12, 24], "expiry":[24, 48, 72, 144, 288], "fontSize":range(12,24), "orientation":["Automatic", "Landscape", "Portrait"], "artFontSize":[10, 12, 14, 16, 18, 20], "feedsort":["Manual", "Most unread", "Least unread", "Most recent", "Least recent"] }
titles = {"updateInterval":"Auto-update interval", "expiry":"Delete articles", "fontSize":"List font size", "orientation":"Display orientation", "artFontSize":"Article font size","feedsort":"Feed sort order"}
subtitles = {"updateInterval":"Every %s hours", "expiry":"After %s hours", "fontSize":"%s pixels", "orientation":"%s", "artFontSize":"%s pixels", "feedsort":"%s"}

class Config():
    def __init__(self, parent, configFilename):
        self.configFilename = configFilename
        self.parent = parent
        # Load config
        self.loadConfig()

        # Backup current settings for later restore
        self.config_backup = dict(self.config)
        self.do_restore_backup = True

    def on_save_button_clicked(self, button):
        self.do_restore_backup = False
        self.window.destroy()

    def createDialog(self):
        
        self.window = gtk.Dialog("Settings", self.parent)
        self.window.set_geometry_hints(min_height=600)

        save_button = self.window.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        save_button.connect('clicked', self.on_save_button_clicked)
        #self.window.set_default_size(-1, 600)
        panArea = hildon.PannableArea()
        
        vbox = gtk.VBox(False, 2)
        self.buttons = {}

        def heading(text):
            l = gtk.Label()
            l.set_size_request(-1, 6)
            vbox.pack_start(l, expand=False)
            vbox.pack_start(gtk.Frame(text), expand=False)

        def add_setting(setting):
            picker = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            selector = self.create_selector(ranges[setting], setting)
            picker.set_selector(selector)
            picker.set_title(titles[setting])
            picker.set_text(titles[setting], subtitles[setting] % self.config[setting])
            picker.set_name('HildonButton-finger')
            picker.set_alignment(0,0,1,1)
            self.buttons[setting] = picker
            vbox.pack_start(picker, expand=False)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("View Known Issues and Tips")
        button.connect("clicked", self.button_tips_clicked)
        button.set_alignment(0,0,1,1)
        vbox.pack_start(button, expand=False)  

        heading('Display')
        add_setting('fontSize')
        add_setting('artFontSize')
        add_setting('orientation')
        add_setting('feedsort')
        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Hide read feeds")
        button.set_active(self.config["hidereadfeeds"])
        button.connect("toggled", self.button_toggled, "hidereadfeeds")
        vbox.pack_start(button, expand=False)

        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Hide read articles")
        button.set_active(self.config["hidereadarticles"])
        button.connect("toggled", self.button_toggled, "hidereadarticles")
        vbox.pack_start(button, expand=False)


        heading('Updating')
        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Automatically update feeds")
        button.set_active(self.config["autoupdate"])
        button.connect("toggled", self.button_toggled, "autoupdate")
        vbox.pack_start(button, expand=False)
        add_setting('updateInterval')
        add_setting('expiry')

        heading('Network')
        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label('Cache images')
        button.set_active(self.config["imageCache"])
        button.connect("toggled", self.button_toggled, "imageCache")
        vbox.pack_start(button, expand=False)

        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Use HTTP proxy")
        button.set_active(self.config["proxy"])
        button.connect("toggled", self.button_toggled, "proxy")
        vbox.pack_start(button, expand=False)
        
        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label('Open links in external browser')
        button.set_active(self.config["extBrowser"])
        button.connect("toggled", self.button_toggled, "extBrowser")
        vbox.pack_start(button, expand=False)
        
        panArea.add_with_viewport(vbox)
        
        self.window.vbox.add(panArea)
        self.window.connect("destroy", self.onExit)
        #self.window.add(self.vbox)
        self.window.set_default_size(-1, 600)
        self.window.show_all()
        return self.window

    def button_tips_clicked(self, *widget):
        import dbus
        bus = dbus.SessionBus()
        proxy = bus.get_object("com.nokia.osso_browser", "/com/nokia/osso_browser/request")
        iface = dbus.Interface(proxy, 'com.nokia.osso_browser')
        iface.open_new_window("http://feedingit.marcoz.org/news/?page_id=%s" % VERSION)

    def onExit(self, *widget):
        # When the dialog is closed without hitting
        # the "Save" button, restore the configuration
        if self.do_restore_backup:
            print 'Restoring configuration'
            self.config = self.config_backup

        self.saveConfig()
        self.window.destroy()

    def button_toggled(self, widget, configName):
        #print "widget", widget.get_active()
        if (widget.get_active()):
            self.config[configName] = True
        else:
            self.config[configName] = False
        #print "autoup",  self.autoupdate
        self.saveConfig()
        
    def selection_changed(self, selector, button, setting):
        current_selection = selector.get_current_text()
        if current_selection:
            self.config[setting] = current_selection
        idle_add(self.updateButton, setting)
        self.saveConfig()
        
    def updateButton(self, setting):
        self.buttons[setting].set_text(titles[setting], subtitles[setting] % self.config[setting])
        
    def loadConfig(self):
        self.config = {}
        try:
            configParser = RawConfigParser()
            configParser.read(self.configFilename)
            self.config["fontSize"] = configParser.getint(section, "fontSize")
            self.config["artFontSize"] = configParser.getint(section, "artFontSize")
            self.config["expiry"] = configParser.getint(section, "expiry")
            self.config["autoupdate"] = configParser.getboolean(section, "autoupdate")
            self.config["updateInterval"] = configParser.getfloat(section, "updateInterval")
            self.config["orientation"] = configParser.get(section, "orientation")
            self.config["imageCache"] = configParser.getboolean(section, "imageCache")
        except:
            self.config["fontSize"] = 17
            self.config["artFontSize"] = 14
            self.config["expiry"] = 24
            self.config["autoupdate"] = False
            self.config["updateInterval"] = 4
            self.config["orientation"] = "Automatic"
            self.config["imageCache"] = False
        try:
            self.config["proxy"] = configParser.getboolean(section, "proxy")
        except:
            self.config["proxy"] = True
        try:
            self.config["hidereadfeeds"] = configParser.getboolean(section, "hidereadfeeds")
            self.config["hidereadarticles"] = configParser.getboolean(section, "hidereadarticles")
        except:
            self.config["hidereadfeeds"] = False
            self.config["hidereadarticles"] = False
        try:
            self.config["extBrowser"] = configParser.getboolean(section, "extBrowser")
        except:
            self.config["extBrowser"] = False
        try:
            self.config["feedsort"] = configParser.get(section, "feedsort")
        except:
            self.config["feedsort"] = "Manual"
        
    def saveConfig(self):
        configParser = RawConfigParser()
        configParser.add_section(section)
        configParser.set(section, 'fontSize', str(self.config["fontSize"]))
        configParser.set(section, 'artFontSize', str(self.config["artFontSize"]))
        configParser.set(section, 'expiry', str(self.config["expiry"]))
        configParser.set(section, 'autoupdate', str(self.config["autoupdate"]))
        configParser.set(section, 'updateInterval', str(self.config["updateInterval"]))
        configParser.set(section, 'orientation', str(self.config["orientation"]))
        configParser.set(section, 'imageCache', str(self.config["imageCache"]))
        configParser.set(section, 'proxy', str(self.config["proxy"]))
        configParser.set(section, 'hidereadfeeds', str(self.config["hidereadfeeds"]))
        configParser.set(section, 'hidereadarticles', str(self.config["hidereadarticles"]))
        configParser.set(section, 'extBrowser', str(self.config["extBrowser"]))
        configParser.set(section, 'feedsort', str(self.config["feedsort"]))

        # Writing our configuration file
        file = open(self.configFilename, 'wb')
        configParser.write(file)
        file.close()

    def create_selector(self, choices, setting):
        #self.pickerDialog = hildon.PickerDialog(self.parent)
        selector = hildon.TouchSelector(text=True)
        index = 0
        for item in choices:
            iter = selector.append_text(str(item))
            if str(self.config[setting]) == str(item): 
                selector.set_active(0, index)
            index += 1
        selector.connect("changed", self.selection_changed, setting)
        #self.pickerDialog.set_selector(selector)
        return selector
        #self.pickerDialog.show_all()

    def getFontSize(self):
        return self.config["fontSize"]
    def getArtFontSize(self):
        return self.config["artFontSize"]
    def getExpiry(self):
        return self.config["expiry"]
    def isAutoUpdateEnabled(self):
        return self.config["autoupdate"]
    def getUpdateInterval(self):
        return float(self.config["updateInterval"])
    def getReadFont(self):
        return "sans italic %s" % self.config["fontSize"]
    def getUnreadFont(self):
        return "sans %s" % self.config["fontSize"]
    def getOrientation(self):
        return ranges["orientation"].index(self.config["orientation"])
    def getImageCache(self):
        return self.config["imageCache"]
    def getProxy(self):
        if self.config["proxy"] == False:
            return (False, None)
        if client_get_default().get_bool('/system/http_proxy/use_http_proxy'):
            port = client_get_default().get_int('/system/http_proxy/port')
            http = client_get_default().get_string('/system/http_proxy/host')
            proxy = ProxyHandler( {"http":"http://%s:%s/"% (http,port)} )
            return (True, proxy)
        return (False, None)
    def getHideReadFeeds(self):
        return self.config["hidereadfeeds"]
    def getHideReadArticles(self):
        return self.config["hidereadarticles"]
    def getOpenInExternalBrowser(self):
        return self.config["extBrowser"]
    def getFeedSortOrder(self):
        return self.config["feedsort"]
