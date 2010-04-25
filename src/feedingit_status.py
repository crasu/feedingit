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
import hildondesktop

class FeedingItStatusPlugin(hildondesktop.StatusMenuItem):
    def __init__(self):
        hildondesktop.StatusMenuItem.__init__(self)

        icon_theme = gtk.icon_theme_get_default()
        pixbuf = icon_theme.load_icon("feedingit", 22, gtk.ICON_LOOKUP_NO_SVG)
        self.set_status_area_icon(pixbuf)

        label = gtk.Label("Example message")
        self.add(label)
        self.show_all()

hd_plugin_type = FeedingItStatusPlugin