# -*- coding: utf-8 -*-
################################################################################
#
# begin:      2020-05-08
# copyright:  (C) 2020 by OpenGeoGroep
# email:      info@opengeogroep.nl

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
################################################################################

from ImaerPlugin.imaer_plugin_base import ImaerPluginBase


class ImaerPluginNl(ImaerPluginBase):

    def __init__(self, iface):
        print('ImaerPlugin NL: __init__()')
        super().__init__(iface)

        self.name = 'AERIUS'

        self.action_configuration = [
            {
                'name': 'generate_calc_input',
                'icon': 'icon_generate_calc_input.svg',
                'tool_tip': 'Generate IMAER Calculator input gml',
                'triggered_slot': self.run_generate_calc_input
            }, {
                'name': 'import_calc_result',
                'icon': 'icon_import_calc_result.svg',
                'tool_tip': 'Import IMAER Calculator result GML',
                'triggered_slot': self.run_import_calc_result
            }, {
                'name': 'relate_calc_results',
                'icon': 'icon_relate_calc_results.svg',
                'tool_tip': 'Relate Calculation results',
                'triggered_slot': self.run_relate_calc_results
            }, {
                'name': 'connect_receptorsets',
                'icon': 'icon_connect_receptorsets.svg',
                'tool_tip': 'Receptor Sets',
                'triggered_slot': self.open_connect_receptorsets
            }, {
                'name': 'connect_jobs',
                'icon': 'icon_connect_jobs.svg',
                'tool_tip': 'Jobs',
                'triggered_slot': self.open_connect_jobs
            }, {
                'name': 'configuration',
                'icon': 'icon_configuration.svg',
                'tool_tip': 'Configure',
                'triggered_slot': self.open_configuration
            }, {
                'name': 'documentation',
                'icon': 'icon_documentation.svg',
                'tool_tip': 'Open online documentation',
                'triggered_slot': self.open_online_documentation
            }
        ]

    def initGui(self):
        print('ImaerPlugin NL: initGui()')
        super().initGui()
        
        if True: #self.dev:
            self.toolbar.setStyleSheet("QToolBar { background-color: rgba(200, 200, 180, 255); }")

    def update_all_widgets(self):
        super().update_all_widgets()
        self.update_connect_widgets()