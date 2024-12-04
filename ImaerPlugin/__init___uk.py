# -*- coding: utf-8 -*-

################################################################################
# A QGIS plugin for generating AERIUS Calculator input IMAER files and
# importing AERIUS Calculator output IMAER files.
#
# begin:      2020-05-08
# copyright:  (C) 2020 by OpenGeoGroep
# email:      info@opengeogroep.nl

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
################################################################################

from .imaer_plugin import ImaerPluginUk


def classFactory(iface):
    return ImaerPluginUk(iface)
