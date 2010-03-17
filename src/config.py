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
# Version     : 0.4.3
# Description : Simple RSS Reader
# ============================================================================

import gtk
import hildon
import ConfigParser
import gobject
import gconf
import urllib2

section = "FeedingIt"
ranges = { "updateInterval":[0.5, 1, 2, 4, 12, 24], "expiry":[24, 48, 72], "fontSize":range(12,24), "orientation":["Automatic", "Landscape", "Portrait"], "artFontSize":[10, 12, 14, 16, 18, 20]}
titles = {"updateInterval":"Auto-update Interval", "expiry":"Expiry For Articles", "fontSize":"Font Size For Article Listing", "orientation":"Display Orientation", "artFontSize":"Font Size For Articles"}
subtitles = {"updateInterval":"Update every %s hours", "expiry":"Delete articles after %s hours", "fontSize":"%s pixels", "orientation":"%s", "artFontSize":"%s pixels"}

class Config():
    def __init__(self, parent, configFilename, has_webkit):
        self.configFilename = configFilename
        self.parent = parent
        self.has_webkit = has_webkit
        # Load config
        self.loadConfig()
        
    def createDialog(self):
        
        self.window = gtk.Dialog("Preferences", self.parent)
        self.window.set_default_size(-1, 600)
        panArea = hildon.PannableArea()
        
        vbox = gtk.VBox(False, 10)
        self.buttons = {}
        if self.has_webkit:
            settings = ["fontSize", "artFontSize", "expiry", "orientation", "updateInterval",]
        else:
            settings = ["fontSize", "expiry", "orientation", "updateInterval",]
        for setting in settings:
            picker = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            selector = self.create_selector(ranges[setting], setting)
            picker.set_selector(selector)
            picker.set_title(titles[setting])
            picker.set_text(titles[setting], subtitles[setting] % self.config[setting])
            picker.set_name('HildonButton-finger')
            picker.set_alignment(0,0,1,1)
            self.buttons[setting] = picker
            vbox.pack_start(picker, expand=False)
        
        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Auto-update Enabled")
        button.set_active(self.config["autoupdate"])
        button.connect("toggled", self.button_toggled, "autoupdate")
        vbox.pack_start(button, expand=False)

        if self.has_webkit:
            button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
            button.set_label("Webkit Articles Enabled")
            button.set_active(self.config["webkit"])
            button.connect("toggled", self.button_toggled, "webkit")
            vbox.pack_start(button, expand=False)
        
        panArea.add_with_viewport(vbox)
        
        self.window.vbox.add(panArea)        
        self.window.connect("destroy", self.onExit)
        #self.window.add(self.vbox)
        self.window.show_all()
        return self.window

    def onExit(self, *widget):
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
        gobject.idle_add(self.updateButton, setting)
        self.saveConfig()
        
    def updateButton(self, setting):
        self.buttons[setting].set_text(titles[setting], subtitles[setting] % self.config[setting])
        
    def loadConfig(self):
        self.config = {}
        try:
            configParser = ConfigParser.RawConfigParser()
            configParser.read(self.configFilename)
            self.config["fontSize"] = configParser.getint(section, "fontSize")
            self.config["artFontSize"] = configParser.getint(section, "artFontSize")
            self.config["expiry"] = configParser.getint(section, "expiry")
            self.config["autoupdate"] = configParser.getboolean(section, "autoupdate")
            self.config["updateInterval"] = configParser.getfloat(section, "updateInterval")
            self.config["orientation"] = configParser.get(section, "orientation")
            self.config["webkit"] = configParser.getboolean(section, "webkit")
        except:
            self.config["fontSize"] = 17
            self.config["artFontSize"] = 14
            self.config["expiry"] = 24
            self.config["autoupdate"] = False
            self.config["updateInterval"] = 4
            self.config["orientation"] = "Automatic"
            self.config["webkit"] = self.has_webkit
        
    def saveConfig(self):
        configParser = ConfigParser.RawConfigParser()
        configParser.add_section(section)
        configParser.set(section, 'fontSize', str(self.config["fontSize"]))
        configParser.set(section, 'artFontSize', str(self.config["artFontSize"]))
        configParser.set(section, 'expiry', str(self.config["expiry"]))
        configParser.set(section, 'autoupdate', str(self.config["autoupdate"]))
        configParser.set(section, 'updateInterval', str(self.config["updateInterval"]))
        configParser.set(section, 'orientation', str(self.config["orientation"]))
        configParser.set(section, 'webkit', str(self.config["webkit"]))

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
        return "sans %s" % self.config["fontSize"]
    def getUnreadFont(self):
        return "sans bold %s" % self.config["fontSize"]
    def getOrientation(self):
        return ranges["orientation"].index(self.config["orientation"])
    def getWebkitSupport(self):
        if self.has_webkit:
            return self.config["webkit"]
        else:
            return False
    def getProxy(self):
        if gconf.client_get_default().get_bool('/system/http_proxy/use_http_proxy'):
            port = gconf.client_get_default().get_int('/system/http_proxy/port')
            http = gconf.client_get_default().get_string('/system/http_proxy/host')
            proxy = proxy = urllib2.ProxyHandler( {"http":"http://%s:%s/"% (http,port)} )
            return (True, proxy)
        return (False, None)