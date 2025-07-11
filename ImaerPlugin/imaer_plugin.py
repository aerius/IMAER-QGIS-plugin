# -*- coding: utf-8 -*-
################################################################################
#
# begin:      2020-05-08
# copyright:  (C) 2020 by Raymond Nijssen, AERIUS
# email:      r.nijssen@terglobo.nl

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
################################################################################

import os
import time
import webbrowser
import pathlib

from qgis.PyQt.QtWidgets import QAction, QFileDialog, QDialogButtonBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QStandardPaths, Qt

from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsVectorLayer,
    QgsField,
    QgsProject,
    QgsApplication,
    QgsExpressionContextUtils,
    QgsCoordinateTransform,
    QgsSettings,
    QgsCsException)
from qgis.gui import QgsMapLayerComboBox

from ImaerPlugin.tasks import ImportImaerCalculatorResultTask
from ImaerPlugin.algs.provider import ImaerProvider
from ImaerPlugin.generate_calc_input import GenerateCalcInputDialog
from ImaerPlugin.configuration import ConfigurationDialog
from ImaerPlugin.connect_receptorsets import ConnectReceptorSetsDialog
from ImaerPlugin.connect_jobs import ConnectJobsDialog
from ImaerPlugin.relate_calc_results import RelateCalcResultsDialog

from ImaerPlugin.connect import (
    AeriusConnection,
    AeriusOpenData
)

from ImaerPlugin.imaer6 import ImaerDocument
from ImaerPlugin.gpkg import ImaerGpkg
from ImaerPlugin.styles import StyleFactory
from ImaerPlugin.gpkg import ImaerGpkgFieldFactory
from ImaerPlugin.config import ui_settings


class ImaerPlugin:

    def __init__(self, iface):
        # Variable self.dev is set to True if a global variable terglobo_dev exists
        # holding the lowercase value 'on'. This is to ensure that any dev tricks
        # will never be visible for other plugin users.
        dev = QgsExpressionContextUtils.globalScope().variable('terglobo_dev')
        self.dev = dev is not None and dev == 'on'

        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        self.task_manager = QgsApplication.taskManager()
        self.provider = None
        self.imaer_calc_layers = {}
        self.settings = QgsSettings()
        self.version = '3.6.3'
        self.imaer_doc = ImaerDocument()
        self.imaer_gpkg = ImaerGpkg(None)
        self.imaer_gpkg_field_factory = ImaerGpkgFieldFactory()
        self.style_factory = StyleFactory(self)

        # TODO: Make a future proof generic solution for URL management

        # Create connection. For now simply overwrite connect settings from config.
        connect_base_url = ui_settings['connect_url']['NL']
        self.settings.setValue('imaer_plugin/connect_base_url', connect_base_url)
        connect_version = ui_settings['connect_version']['NL']
        self.settings.setValue('imaer_plugin/connect_version', connect_version)
        connect_key = self.settings.value('imaer_plugin/connect_key', defaultValue='')
        do_check_connection = True

        country = self.settings.value('imaer_plugin/country')
        if country not in ui_settings['connect_countries']:
            connect_base_url = None
            connect_version = None
            do_check_connection = False

        self.aerius_connection = AeriusConnection(self, base_url=connect_base_url, version=connect_version, api_key=connect_key, do_check_connection=do_check_connection)
        self.log(self.aerius_connection, user='user')

        # Create dialogs
        work_dir = self.settings.value('imaer_plugin/work_dir', defaultValue=None)
        self.calc_result_file_dialog = QFileDialog(directory=work_dir)
        self.calc_input_file_dialog = QFileDialog(directory=work_dir)

        self.generate_calc_input_dlg = GenerateCalcInputDialog(self, parent=self.iface.mainWindow())
        self.relate_calc_results_dlg = RelateCalcResultsDialog(self, parent=self.iface.mainWindow())

        self.connect_receptorsets_dlg = ConnectReceptorSetsDialog(self, parent=self.iface.mainWindow())
        self.connect_jobs_dlg = ConnectJobsDialog(self, parent=self.iface.mainWindow())
        self.configuration_dlg = ConfigurationDialog(self, parent=self.iface.mainWindow())

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
        self.actions = {}

    def initGui(self):
        # Create toolbar and actions
        self.toolbar = self.iface.addToolBar("Imaer Toolbar")
        if self.dev:
            self.toolbar.setStyleSheet("QToolBar { background-color: rgba(200, 180, 200, 255); }")

        for action_config in self.action_configuration:
            icon = QIcon(os.path.join(self.plugin_dir, 'img', action_config['icon']))
            action = QAction(icon, action_config['tool_tip'], self.iface.mainWindow())
            action.triggered.connect(action_config['triggered_slot'])
            self.toolbar.addAction(action)
            self.actions[action_config['name']] = action

        # Widget update logic
        self.update_all_widgets()
        self.initProcessing()

    def initProcessing(self):
        self.log('initProcessing()')
        self.provider = ImaerProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        '''Removes all plugin widgets and connections'''

        # Remove processing provider
        QgsApplication.processingRegistry().removeProvider(self.provider)

        # Clean up actions and toolbar
        for action_config in self.action_configuration:
            name = action_config['name']
            action = self.actions[name]
            action.triggered.disconnect(action_config['triggered_slot'])
            self.toolbar.removeAction(action)
            del action
            self.actions.pop(name)

        del self.toolbar

        # TODO (?) Delete all plugin dialogs?
        # del self.relate_calc_results_dlg
        self.log('ImaerPlugin unloaded', user='dev')

    def log(self, message, tab='IMAER Plugin', lvl='Info', bar=False, user='user', duration=3):
        # lvl: Info, Warning, Critical, Success
        # user: user, dev
        level = getattr(Qgis, lvl)
        if bar or (user == 'user') or (user == 'dev' and self.dev):
            QgsMessageLog.logMessage(str(message), tab, level=level)
        if bar:
            self.iface.messageBar().pushMessage(lvl, str(message), level, duration=duration)

    def run_import_calc_result(self, checked=False, gml_fns=None):
        if gml_fns is None:
            gml_fns, _ = self.calc_result_file_dialog.getOpenFileNames(caption="Open Calculator result GML file", filter='*.gml', parent=self.iface.mainWindow())
            self.log(f'gml_fns: {gml_fns}')
            # print(gml_fns)
        
        if gml_fns == []:
            # print('no files selected')
            return

        for gml_fn in gml_fns:
            if gml_fn == '' or gml_fn is None:
                return

            gml_path = os.path.dirname(gml_fn)
            if not os.access(gml_path, os.W_OK):
                self.log(f'Cannot create .gpkg file in gml directory: {gml_path}', lvl='Critical', bar=True, duration=5)
                return

            gml_stem, _ = os.path.splitext(gml_fn)
            gpkg_fn = f'{gml_stem}.gpkg'

            if os.path.exists(gpkg_fn):  # TODO Warn for overwriting?
                pass
                # self.log(f'Gpkg file already exists: {gpkg_fn}', lvl='Warning', bar=True, duration=5)

            task = ImportImaerCalculatorResultTask(self, gml_fn, gpkg_fn, self.import_calc_result_callback)
            task_result = self.task_manager.addTask(task)
            self.log(f'task result: {task_result}')

    def import_calc_result_callback(self, result, gpkg_fn=None):
        # self.log(result)
        if result['status'] == 'ok':
            self.load_calculation_results_gpkg(gpkg_fn)
        elif result['status'] == 'error':
            self.log(result['message'], lvl='Critical', bar=True, duration=10)
        elif result['status'] == 'warning':
            self.log(result['message'], lvl='Warning', bar=True, duration=10)
        else:
            self.log('Something unexpected went wrong (import_calc_result_callback)')

    def load_calculation_results_gpkg(self, gpkg_fn, layer_names=None, zoom=True, make_groups=True):
        '''Callback function from the import task after finishing the gpkg'''

        result_layer_names = ['receptor_hexagons', 'receptor_points', 'sub_points', 'calculation_points']
        if make_groups:
            result_layer_names.reverse()

        if layer_names is not None:
            result_layer_names = set(result_layer_names).intersection(set(layer_names))

        base = os.path.basename(gpkg_fn)
        stem, ext = os.path.splitext(base)

        imaer_metadata_source = f'{gpkg_fn}|layername=imaer_metadata'
        imaer_metadata_layer = QgsVectorLayer(imaer_metadata_source, 'md', 'ogr')

        situation_name = ''
        for feat in imaer_metadata_layer.getFeatures():
            if feat['key'] == 'situation_name':
                situation_name = feat['value']

        total_extent = None
        loaded_layer_cnt = 0

        layer_group = None

        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()

        for result_layer_name in result_layer_names:
            layer_data_source = f'{gpkg_fn}|layername={result_layer_name}'
            if make_groups:
                if situation_name == '':
                    layer_name = result_layer_name
                else:
                    layer_name = f'{situation_name} - {result_layer_name}'.strip()
            else:
                layer_name = f'{stem} - {result_layer_name}'
            layer = QgsVectorLayer(layer_data_source, layer_name, 'ogr')
            if not layer.isValid():
                continue

            layer_crs = layer.crs()
            extent_transform = QgsCoordinateTransform(layer_crs, canvas_crs, QgsProject.instance())

            try:
                layer_extent = extent_transform.transformBoundingBox(layer.extent())
            except QgsCsException:
                layer_extent = None

            if layer_extent is not None:
                if total_extent is None:
                    total_extent = layer_extent
                else:
                    total_extent.combineExtentWith(layer_extent)

            if make_groups and (layer_group is None):
                root = QgsProject.instance().layerTreeRoot()
                temp_group = root.addGroup(stem)
                layer_group = temp_group.clone()
                root.insertChildNode(0, layer_group)
                root.removeChildNode(temp_group)

            if make_groups:
                QgsProject.instance().addMapLayer(layer, False)
                layer_group.addLayer(layer)
            else:
                QgsProject.instance().addMapLayer(layer)

            # Set styles (renderers and labels) TODO: Use set_imaer_styles
            style_name = 'contribution'

            if result_layer_name == 'receptor_hexagons':
                renderer = self.style_factory.create_renderer(style_name, 'polygon')
                exp = '"deposition_nox_nh3_sum"'
                renderer.setClassAttribute(exp)
                labeling = self.style_factory.create_labeling(exp)
                self.add_layer_style(layer, renderer, f'{style_name}_deposition', labeling)

            elif result_layer_name == 'receptor_points':
                renderer = self.style_factory.create_renderer(style_name, 'point')
                exp = 'coalesce("concentration_nox", 0) + coalesce("concentration_no2", 0) + coalesce("concentration_nh3", 0)'
                renderer.setClassAttribute(exp)
                labeling = self.style_factory.create_labeling(exp)
                self.add_layer_style(layer, renderer, f'{style_name}_concentration', labeling)

            elif result_layer_name == 'sub_points':
                renderer = self.style_factory.create_renderer(style_name, 'point')
                exp = '"deposition_nox_nh3_sum"'
                renderer.setClassAttribute(exp)
                labeling = self.style_factory.create_labeling(exp)
                self.add_layer_style(layer, renderer, f'{style_name}_deposition', labeling)

                renderer = self.style_factory.create_renderer(style_name, 'point')
                exp = 'coalesce("concentration_nox", 0) + coalesce("concentration_no2", 0) + coalesce("concentration_nh3", 0)'
                renderer.setClassAttribute(exp)
                labeling = self.style_factory.create_labeling(exp)
                self.add_layer_style(layer, renderer, f'{style_name}_concentration', labeling)

            elif result_layer_name == 'calculation_points':
                renderer = self.style_factory.create_renderer(style_name, 'point')
                exp = '"deposition_nox_nh3_sum"'
                renderer.setClassAttribute(exp)
                labeling = self.style_factory.create_labeling(exp)
                self.add_layer_style(layer, renderer, f'{style_name}_deposition', labeling)

                renderer = self.style_factory.create_renderer(style_name, 'point')
                exp = 'coalesce("concentration_nox", 0) + coalesce("concentration_no2", 0) + coalesce("concentration_nh3", 0)'
                renderer.setClassAttribute(exp)
                labeling = self.style_factory.create_labeling(exp)
                self.add_layer_style(layer, renderer, f'{style_name}_concentration', labeling)

            loaded_layer_cnt += 1

        if zoom and (total_extent is not None):
            canvas = self.iface.mapCanvas()
            total_extent.scale(1.2)
            canvas.setExtent(total_extent)

        if loaded_layer_cnt == 0:
            self.log(f'No result layers found in {stem}.gml', lvl='Warning', bar=True, duration=5)
        else:
            pass
            #self.log(f'Loaded {loaded_layer_cnt} result layers.', lvl='Info', bar=True, duration=3)

    def set_imaer_styles(self, layer, style_name, labeling=None):
        field_names = layer.fields().names()

        if layer.geometryType() == 0:
            geometry_type = 'point'
        elif layer.geometryType() == 2:
            geometry_type = 'polygon'
        else:
            return

        if 'deposition_nox_nh3_sum' in field_names:
            renderer = self.style_factory.create_renderer(style_name, geometry_type)
            exp = '"deposition_nox_nh3_sum"'
            renderer.setClassAttribute(exp)
            labeling = self.style_factory.create_labeling(exp)
            self.add_layer_style(layer, renderer, f'{style_name}_deposition', labeling)

        if set(['concentration_nox', 'concentration_no2', 'concentration_nh3']).issubset(field_names):
            renderer = self.style_factory.create_renderer(style_name, geometry_type)
            exp = 'coalesce("concentration_nox", 0) + coalesce("concentration_no2", 0) + coalesce("concentration_nh3", 0)'
            renderer.setClassAttribute(exp)
            labeling = self.style_factory.create_labeling(exp)
            self.add_layer_style(layer, renderer, f'{style_name}_concentration', labeling)

    def add_layer_style(self, layer, renderer, layer_style_name, labeling=None):
        if renderer is not None:
            style_manager = layer.styleManager()
            style_manager.addStyleFromLayer(layer_style_name)
            style_manager.setCurrentStyle(layer_style_name)
            layer.setRenderer(renderer)
            if labeling is not None:
                layer.setLabeling(labeling)
                # layer.setLabelsEnabled(True)

    def get_imaer_calc_metadata(self, layer):
        '''Returns IMAER gpkg metadata from cache or attempts
        to find metadata.'''
        if layer is None:
            return

        layer_id = layer.id()

        if layer_id in self.imaer_calc_layers:
            return self.imaer_calc_layers[layer_id]
        else:
            self.imaer_calc_layers[layer_id] = {'is_imaer_calc_layer': False}

        self.imaer_calc_layers[layer_id]['imaer_contribution_layer'] = self.is_contribution_layer(layer)

        if not isinstance(layer, QgsVectorLayer):
            return self.imaer_calc_layers[layer_id]

        provider = layer.dataProvider()
        if not provider.wkbType() in [1, 3]:
            return self.imaer_calc_layers[layer_id]

        ds = provider.dataSourceUri()
        if '|layername=' in ds:
            gpkg_fn, gpkg_layer = ds.split('|layername=')
        else:
            return self.imaer_calc_layers[layer_id]
        if gpkg_layer not in ['receptor_hexagons', 'receptor_points', 'sub_points', 'calculation_points']:
            return self.imaer_calc_layers[layer_id]

        metadata_ds = '{}|layername=imaer_metadata'.format(gpkg_fn)
        try:
            md_layer = QgsVectorLayer(metadata_ds, 'metadata', 'ogr')
        except:
            return self.imaer_calc_layers[layer_id]
        for md_feat in md_layer.getFeatures():
            self.imaer_calc_layers[layer_id][md_feat[1]] = md_feat[2]
        self.imaer_calc_layers[layer_id]['is_imaer_calc_layer'] = True
        self.imaer_calc_layers[layer_id]['gpkg_fn'] = gpkg_fn
        self.imaer_calc_layers[layer_id]['imaer_layer_type'] = gpkg_layer

        return self.imaer_calc_layers[layer_id]

    def is_contribution_layer(self, layer):
        if not isinstance(layer, QgsVectorLayer):
            return None

        layer_fields = layer.fields()
        for layer_type in ['receptor_hexagons', 'receptor_points', 'sub_points', 'calculation_points']:
            layer_type_fields = self.imaer_gpkg_field_factory.create_fields_for_layer_type(layer_type)

            if self.contains_fields(layer_type_fields, layer_fields):
                return layer_type
        return None

    def contains_fields(self, fields, mandatory_fields):
        for mandatory_field in mandatory_fields:
            if mandatory_field.name() in ['fid', 'ogc_fid']:
                continue
            field_found = False
            for field in fields:
                if mandatory_field == field:
                    pass
                if mandatory_field == field:
                    field_found = True
            if not field_found:
                return False
        return True

    def run_generate_calc_input(self):
        self.log('run_generate_calc_input()', user='dev')
        self.generate_calc_input_dlg.show()
        result = self.generate_calc_input_dlg.exec_()
        if result:
            self.generate_calc_input_dlg.generate_imaer_gml()

    def update_all_widgets(self):
        self.update_crs_widgets()
        self.update_connect_widgets()

    def update_crs_widgets(self):
        epsg_id = self.settings.value('imaer_plugin/crs', defaultValue=None)
        if epsg_id is None:
            self.actions['generate_calc_input'].setEnabled(False)
        else:
            self.actions['generate_calc_input'].setEnabled(True)

    def update_connect_widgets(self):
        country = self.configuration_dlg.combo_country.currentText()
        is_connect_country = country in ui_settings['connect_countries']

        conn_ok = self.aerius_connection.is_valid() and self.aerius_connection.api_key_is_ok
        enable_connect_widgets = conn_ok and is_connect_country

        old_state = self.actions['connect_receptorsets'].isEnabled()

        self.actions['connect_receptorsets'].setEnabled(enable_connect_widgets)
        self.actions['connect_jobs'].setEnabled(enable_connect_widgets)

        # If buttons have been enabled, update dialog tables content.
        if (not old_state) and enable_connect_widgets:
            self.connect_receptorsets_dlg.get_receptor_sets()
            self.connect_jobs_dlg.get_jobs()

    def open_online_documentation(self):
        short_version = '.'.join(self.version.split('.')[:2])  # 3.4.2 -> 3.4
        doc_index_url = f'https://docs.aerius.nl/qgis/{short_version}/00_index'
        webbrowser.open(doc_index_url)

    def open_configuration(self):
        self.log('open_configuration()', user='dev')
        self.configuration_dlg.load_ui_from_settings()
        result = self.configuration_dlg.exec_()
        if result:
            self.configuration_dlg.save_ui_to_settings()
            self.aerius_connection.check_connection()
            self.update_connect_widgets()
            self.update_crs_widgets()

    def open_connect_receptorsets(self):
        self.log('open_connect_receptorsets()', user='dev')
        result = self.connect_receptorsets_dlg.exec_()

    def open_connect_jobs(self):
        self.log('open_connect_jobs()', user='dev')
        result = self.connect_jobs_dlg.exec_()

    def run_relate_calc_results(self):
        result = self.relate_calc_results_dlg.exec_()

        if not result == 1:
            return

        layers = self.relate_calc_results_dlg.get_layer_list()
        layer_name = self.relate_calc_results_dlg.edit_layer_name.text()
        calc_type = self.relate_calc_results_dlg.combo_calc_type.currentText()

        if calc_type == 'difference':
            self.relate_calc_results_dlg.calculate_difference(layers, layer_name)

        if calc_type == 'sum':
            self.relate_calc_results_dlg.calculate_sum(layers, layer_name)

        if calc_type == 'maximum':
            self.relate_calc_results_dlg.calculate_maximum(layers, layer_name)
