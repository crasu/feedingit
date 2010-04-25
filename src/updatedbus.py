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

import dbus
import dbus.service

def get_lock(key):
    try:
        bus_name = dbus.service.BusName('org.marcoz.feedingit.lock_%s' %key,bus=dbus.SessionBus(), do_not_queue=True)
    except:
        bus_name = None
    return bus_name
    

class UpdateServerObject(dbus.service.Object):
    def __init__(self, app):
        # Here the service name
        bus_name = dbus.service.BusName('org.marcoz.feedingit',bus=dbus.SessionBus())
        # Here the object path
        dbus.service.Object.__init__(self, bus_name, '/org/marcoz/feedingit/update')
        self.app = app

    @dbus.service.method('org.marcoz.feedingit')
    def UpdateAll(self):
        self.app.automaticUpdate()
        return "Done"
    
    @dbus.service.method('org.marcoz.feedingit')
    def StopUpdate(self):
        self.app.stopUpdate()
        return "Done"
    
    # A signal that will be exported to dbus
    @dbus.service.signal('org.marcoz.feedingit', signature='')
    def ArticleCountUpdated(self):
        pass

    # A signal that will be exported to dbus
    @dbus.service.signal('org.marcoz.feedingit', signature='')
    def UpdateStarted(self):
        pass
    
    # A signal that will be exported to dbus
    @dbus.service.signal('org.marcoz.feedingit', signature='')
    def UpdateFinished(self):
        pass