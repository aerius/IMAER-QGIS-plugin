# -*- coding: utf-8 -*-
import os
import time
import json

from qgis.PyQt.QtCore import (
    Qt,
    QVariant
)
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QWidget,
    QGroupBox
)
from qgis.PyQt.QtGui import (
    QStandardItem,
    QStandardItemModel,
    QTextDocument
)

from qgis.PyQt import uic

from qgis.utils import iface
from qgis.gui import (
    QgsMapLayerComboBox,
    QgsFieldComboBox
)
from qgis.core import (
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    Qgis
)

from ImaerPlugin.config import (
    emission_sectors,
    ui_settings
)

from ImaerPlugin.time_varying_profile import TimeVaryingProfileDialog

from ImaerPlugin.imaer6 import (
    ADMSRoad,
    AdmsRoadSideBarrier,
    ADMSSourceCharacteristics,
    AeriusCalculatorMetadata,
    Building,
    CalculationPoint,
    CriticalLevel,
    NcaCustomCalculationPoint,
    CustomTimeVaryingProfile,
    CustomVehicle,
    Emission,
    EmissionSource,
    EmissionSourceCharacteristics,
    EmissionSourceType,
    EntityReference,
    ImaerDocument,
    ReferenceTimeVaryingProfile,
    SpecifiedHeatContent,
    SRM2Road,
    Srm2RoadSideBarrier,
    StandardTimeVaryingProfile,
    StandardVehicle
)

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'generate_calc_input_dlg.ui'))


class GenerateCalcInputDialog(QDialog, FORM_CLASS):
    def __init__(self, plugin, parent=None):
        """Constructor."""
        super(GenerateCalcInputDialog, self).__init__(parent)

        self.setupUi(self)
        self.iface = iface
        self.plugin = plugin
        self.time_varying_profile_dlg = TimeVaryingProfileDialog()

        self.emission_tabs = {}
        self.emission_tabs['other'] = getattr(self, 'tab_emission_sources')
        self.emission_tabs['roads'] = getattr(self, 'tab_roads')
        self.emission_tabs['buildings'] = getattr(self, 'tab_buildings')
        self.emission_tabs['calc_points'] = getattr(self, 'tab_calc_points')
        self.emission_tabs['time_varying_profiles'] = getattr(self, 'tab_time_varying_profiles')

        self.imaer_doc = ImaerDocument()

        self.init_gui()

    def init_gui(self):
        # Add message bar

        self.combo_layer_es.setFilters(Qgis.LayerFilter.VectorLayer)
        self.combo_layer_rd.setFilters(Qgis.LayerFilter.LineLayer)
        self.combo_layer_bld.setFilters(Qgis.LayerFilter.PolygonLayer | Qgis.LayerFilter.PointLayer)
        self.combo_layer_cp.setFilters(Qgis.LayerFilter.PointLayer)

        self.group_input_es.toggled.connect(self.update_emission_tab)
        self.radioButton_es.toggled.connect(self.update_emission_tab)
        self.radioButton_rd.toggled.connect(self.update_emission_tab)
        self.checkBox_bld.toggled.connect(self.update_emission_tab)
        self.checkBox_cp.toggled.connect(self.update_emission_tab)
        self.checkBox_tvp.toggled.connect(self.update_emission_tab)

        self.edit_outfile.textChanged.connect(self.update_ok_button)

        self.combo_layer_es.layerChanged.connect(self.update_field_combos)
        self.combo_layer_rd.layerChanged.connect(self.update_field_combos)
        self.combo_layer_bld.layerChanged.connect(self.update_field_combos)
        self.combo_layer_cp.layerChanged.connect(self.update_field_combos)

        self.button_outfile.clicked.connect(self.browse_generate_calc_input_file)

        self.btn_save_settings.clicked.connect(self.save_settings)
        self.btn_load_settings.clicked.connect(self.load_settings)

        self.radio_veh_page_custom.page = self.page_veh_custom
        self.radio_veh_page_eft.page = self.page_veh_eft
        self.radio_veh_page_custom.toggled.connect(self.update_adms_vehicle_page)
        self.radio_veh_page_eft.toggled.connect(self.update_adms_vehicle_page)

        for fcb in self.findChildren(QgsFieldComboBox):
            fcb.setAllowEmptyFieldName(True)

        self.fcb_rd_v_custom_movements_units.addItems([''] + ui_settings['units_veh_movements'])
        self.fcb_rd_v_eft_units.addItems(ui_settings['units_veh_movements'])
        self.fcb_rd_v_eft_units.setCurrentIndex(1)  # Default to 'p/24 hour'

        self.tvp_model = QStandardItemModel()
        self.tvp_model.setHorizontalHeaderItem(0, QStandardItem('localId'))
        self.tvp_model.setHorizontalHeaderItem(1, QStandardItem('label'))
        self.tvp_model.setHorizontalHeaderItem(2, QStandardItem('customType'))
        self.tvp_model.setHorizontalHeaderItem(3, QStandardItem('values'))

        self.tableView_tvp.horizontalHeader().setStretchLastSection(True)
        self.tableView_tvp.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView_tvp.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView_tvp.setSelectionMode(QAbstractItemView.SingleSelection)

        self.tableView_tvp.setModel(self.tvp_model)
        self.tableView_tvp.resizeColumnsToContents()

        self.button_tvp_add.clicked.connect(self.open_time_varying_profile_dlg)
        self.button_tvp_edit.clicked.connect(self.open_time_varying_profile_dlg)
        self.button_tvp_delete.clicked.connect(self.open_time_varying_profile_dlg)
        self.tableView_tvp.selectionModel().selectionChanged.connect(self.update_tvp_buttons)

        # Make sure the corresponding vehicle page is displayed
        self.radio_veh_page_custom.setChecked(True)
        self.stack_rd_veh_adms.setCurrentWidget(self.radio_veh_page_custom.page)

        self.set_fixed_options()
        self.update_field_combos()
        self.update_ok_button()
        self.update_tvp_buttons()
        self.update_emission_tab()

    def __del__(self):
        self.edit_outfile.textChanged.disconnect(self.update_ok_button)
        self.combo_sector.currentIndexChanged.disconnect(self.update_emission_tab)
        self.combo_layer_es.layerChanged.disconnect(self.update_field_combos)
        self.combo_layer_rd.layerChanged.disconnect(self.update_field_combos)
        self.combo_layer_bld.layerChanged.disconnect(self.update_field_combos)
        self.combo_layer_cp.layerChanged.disconnect(self.update_field_combos)
        self.button_outfile.clicked.disconnect(self.browse_generate_calc_input_file)

        self.btn_save_settings.clicked.disconnect(self.save_settings)
        self.btn_load_settings.clicked.disconnect(self.load_settings)

        self.button_tvp_add.clicked.disconnect(self.open_time_varying_profile_dlg)
        self.button_tvp_edit.clicked.disconnect(self.open_time_varying_profile_dlg)
        self.button_tvp_delete.clicked.disconnect(self.open_time_varying_profile_dlg)
        self.tableView_tvp.selectionModel().selectionChanged.disconnect(self.update_tvp_buttons)

        self.group_input_es.toggled.disconnect(self.update_emission_tab)
        self.radioButton_es.toggled.disconnect(self.update_emission_tab)
        self.radioButton_rd.toggled.disconnect(self.update_emission_tab)
        self.checkBox_bld.toggled.disconnect(self.update_emission_tab)
        self.checkBox_cp.toggled.disconnect(self.update_emission_tab)
        self.checkBox_tvp.toggled.disconnect(self.update_emission_tab)

    def browse_generate_calc_input_file(self):
        if self.plugin.dev:
            out_path = '/home/raymond/terglobo/projecten/aerius/202007_calc_input_plugin/demodata/gen_calc_input'
        else:
            out_path = ''
        out_fn = time.strftime("calcinput_%Y%m%d_%H%M%S.gml")
        out_fn = os.path.join(out_path, out_fn)

        gml_outfn, filter = self.plugin.calc_input_file_dialog.getSaveFileName(caption="Save as Calculator input gml file", filter='*.gml', directory=out_fn, parent=self.iface.mainWindow())
        self.edit_outfile.setText(gml_outfn)

    def set_fixed_options(self):
        # country
        self.combo_country.addItem('', '')
        for country in ui_settings['countries']:
            self.combo_country.addItem(country, country)

        # crs
        self.combo_crs.addItem('', '')
        for crs in ui_settings['crs']:
            crs_name = f"{crs['name']} ({crs['srid']})"
            self.combo_crs.addItem(crs_name, crs['srid'])

        # years
        for item in ui_settings['project_years']:
            self.combo_project_year.addItem(str(item), item)
        year_index = self.combo_project_year.findData(ui_settings['project_default_year'])
        self.combo_project_year.setCurrentIndex(year_index)

    def update_emission_tab(self):
        country = self.plugin.settings.value('imaer_plugin/country', defaultValue='')
        country_index = self.combo_country.findData(country)
        self.combo_country.setCurrentIndex(country_index)

        crs_setting = self.plugin.settings.value('imaer_plugin/crs', defaultValue='')
        crs_index = self.combo_crs.findData(crs_setting)
        self.combo_crs.setCurrentIndex(crs_index)

        # situation
        self.edit_situation_name.setText('')
        self.combo_situation_type.clear()
        if not country == '':
            self.edit_situation_name.setText(ui_settings['situation_name'][country])

            for item in ui_settings['situation_types_gml'][country]:
                self.combo_situation_type.addItem(item, item)

        # Remove all tabs but 'Metadata'
        while self.tabs_mapping.count() > 1:
            self.tabs_mapping.removeTab(1)
        # Add selected emission tab
        '''
        sector = self.combo_sector.currentData()
        if sector in self.emission_tabs:
            sector_name = emission_sectors[sector]['tab_name']
            self.tabs_mapping.insertTab(1, self.emission_tabs[sector], sector_name)
            self.tabs_mapping.setCurrentIndex(1)
        '''
        n = 1
        if self.group_input_es.isChecked() and self.radioButton_es.isChecked():
            sector1 = 'other'
            sector_name = emission_sectors[sector1]['tab_name']
            self.tabs_mapping.insertTab(n, self.emission_tabs[sector1], sector_name)
            self.tabs_mapping.setCurrentIndex(n)
            n += 1
        else:
            sector1 = None

        if self.group_input_es.isChecked() and self.radioButton_rd.isChecked():
            sector2 = 'roads'
            sector_name = emission_sectors[sector2]['tab_name']
            self.tabs_mapping.insertTab(n, self.emission_tabs[sector2], sector_name)
            self.tabs_mapping.setCurrentIndex(n)
            n += 1
        else:
            sector2 = None

        if self.checkBox_bld.isChecked():
            sector3 = 'buildings'
            sector_name = emission_sectors[sector3]['tab_name']
            self.tabs_mapping.insertTab(n, self.emission_tabs[sector3], sector_name)
            self.tabs_mapping.setCurrentIndex(n)
            n += 1
        else:
            sector3 = None

        if self.checkBox_cp.isChecked():
            sector4 = 'calc_points'
            sector_name = emission_sectors[sector4]['tab_name']
            self.tabs_mapping.insertTab(n, self.emission_tabs[sector4], sector_name)
            self.tabs_mapping.setCurrentIndex(n)
            n += 1
        else:
            sector4 = None

        if self.checkBox_tvp.isChecked():
            sector5 = 'time_varying_profiles'
            sector_name = emission_sectors[sector5]['tab_name']
            self.tabs_mapping.insertTab(n, self.emission_tabs[sector5], sector_name)
            self.tabs_mapping.setCurrentIndex(n)
            n += 1
        else:
            sector5 = None

        # Enable/disable widgets per country
        if country == '' or crs_setting == '':
            return
            # TODO: Raise error

        for sector in [sector1, sector2, sector3, sector4, sector5]:
            if sector in emission_sectors and 'ui_settings' in emission_sectors[sector]:
                # Running this loop multiple times because looping all objects of the QWidget
                # class resulted in a frozen dialog.
                for widget in self.findChildren(QgsFieldComboBox):
                    if widget.objectName() in emission_sectors[sector]['ui_settings'][country]['disable_widgets']:
                        widget.setVisible(False)
                    else:
                        widget.setVisible(True)
                for widget in self.findChildren(QLabel):
                    if widget.objectName() in emission_sectors[sector]['ui_settings'][country]['disable_widgets']:
                        widget.setVisible(False)
                    else:
                        widget.setVisible(True)
                for widget in self.findChildren(QGroupBox):
                    if widget.objectName() in emission_sectors[sector]['ui_settings'][country]['disable_widgets']:
                        widget.setVisible(False)
                    else:
                        widget.setVisible(True)
                if 'emission_tab' in emission_sectors[sector]:
                    try:
                        vehicle_page = emission_sectors[sector]['ui_settings'][country]['vehicle_page']
                        # print(vehicle_page)
                        stack = getattr(self, 'stack_rd_veh')
                        page = getattr(self, vehicle_page)
                        stack.setCurrentWidget(page)
                    except(KeyError):
                        pass

    def update_field_combos(self):
        for fcb in self.findChildren(QgsFieldComboBox):
            if 'fcb_es_' in fcb.objectName():
                fcb.setLayer(self.combo_layer_es.currentLayer())
            if 'fcb_rd_' in fcb.objectName():
                fcb.setLayer(self.combo_layer_rd.currentLayer())
            if 'fcb_bld_' in fcb.objectName():
                fcb.setLayer(self.combo_layer_bld.currentLayer())
            if 'fcb_cp_' in fcb.objectName():
                fcb.setLayer(self.combo_layer_cp.currentLayer())
            if 'fcb_em_' in fcb.objectName():
                fcb.setLayer(self.combo_layer_es.currentLayer())

        # if bld is a point layer then show the diameter field
        if self.combo_layer_bld.currentLayer() is not None:
            if self.combo_layer_bld.currentLayer().geometryType() == 0:
                self.fcb_bld_diameter.setVisible(True)
                self.label_bld_diameter.setVisible(True)
            else:
                self.fcb_bld_diameter.setVisible(False)
                self.label_bld_diameter.setVisible(False)

    def update_ok_button(self):
        if self.edit_outfile.text() == '':
            self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)
            return
        '''
        if self.get_current_sector_id() == 0:
            self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)
            return
        '''
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(True)

    def update_tvp_buttons(self):
        selected_rows = self.tableView_tvp.selectionModel().selectedRows()
        self.button_tvp_edit.setEnabled(len(selected_rows) == 1)
        self.button_tvp_delete.setEnabled(len(selected_rows) == 1)

    def update_adms_vehicle_page(self):
        self.stack_rd_veh_adms.setCurrentWidget(self.sender().page)

    def generate_imaer_gml(self):
        self.plugin.log('starting calcinput generation ...', user='user')
        imaer_doc = self.get_imaer_doc_from_gui()
        if imaer_doc is None:  # Something went wrong during IMAER doc generation...
            self.plugin.log('Something went wrong during IMAER doc generation.')
            return
        fn = self.edit_outfile.text()
        imaer_doc.to_xml_file(fn)
        self.plugin.log('Imaer GML file saved as: <a href="{0}">{0}</a>'.format(fn), lvl='Info', bar=True, duration=10)

    def get_imaer_doc_from_gui(self):
        '''Maps items from GUI widgets to IMAER object'''
        imaer_doc = ImaerDocument()

        # Metadata
        project = {}
        year = self.combo_project_year.currentData()
        project['year'] = year
        description = self.edit_project_description.toPlainText()
        if not description == '':
            project['description'] = description

        situation = None
        if self.group_situation.isChecked():
            situation = {}
            situation_name = self.edit_situation_name.text()
            if not situation_name == '':
                situation['name'] = situation_name
            situation['type'] = self.combo_situation_type.currentText()

        country = self.combo_country.currentData()
        crs_dest_srid = self.combo_crs.currentData()
        crs_dest = QgsCoordinateReferenceSystem.fromEpsgId(crs_dest_srid)

        gml_creator = f'QgisImaerPlugin-{self.plugin.version}'

        metadata = AeriusCalculatorMetadata(
            project=project,
            situation=situation,
            gml_creator=gml_creator
        )

        imaer_doc.metadata = metadata

        # Find all layers to loop
        list_input_layers_to_process = []
        if self.group_input_es.isChecked():
            if self.radioButton_es.isChecked():
                list_input_layers_to_process.append({'layer': self.combo_layer_es.currentLayer(), 'code': 'es'})
            if self.radioButton_rd.isChecked():
                list_input_layers_to_process.append({'layer': self.combo_layer_rd.currentLayer(), 'code': 'rd'})
        if self.checkBox_bld.isChecked():
            list_input_layers_to_process.append({'layer': self.combo_layer_bld.currentLayer(), 'code': 'bld'})
        if self.checkBox_cp.isChecked():
            list_input_layers_to_process.append({'layer': self.combo_layer_cp.currentLayer(), 'code': 'cp'})

        for input_layer in list_input_layers_to_process:
            layer = input_layer['layer']

            crs_source = layer.crs()
            if crs_source == crs_dest:
                crs_transform = None
            else:
                crs_transform = QgsCoordinateTransform(crs_source, crs_dest, QgsProject.instance())

            # Loop all features and create IMAER objects
            for feat in layer.getFeatures():
                local_id = feat.id()

                # geometry
                geom = feat.geometry()
                geom2 = self.make_single_part(geom)
                if geom2 is None:
                    self.plugin.log(f'Input data contains multipart geometry: {geom.asWkt(precision=3)}', bar=True, lvl='Critical')
                    return
                geom = geom2
                # TODO: Check for invalid geometries

                if crs_transform is not None:
                    geom.transform(crs_transform)

                # if it is the emissions source layer, process this
                if input_layer['code'] == 'es':
                    if country == 'NL':
                        es = self.get_emission_source_from_gui(feat, geom, crs_dest_srid, local_id)
                    elif country == 'UK':
                        es = self.get_adms_emission_source_from_gui(feat, geom, crs_dest_srid, local_id)
                    imaer_doc.feature_members.append(es)

                # if it is the road layer process as such
                if input_layer['code'] == 'rd':
                    if country == 'NL':
                        es = self.get_srm2_road_from_gui(feat, geom, crs_dest_srid, local_id)
                    elif country == 'UK':
                        es = self.get_adms_road_from_gui(feat, geom, crs_dest_srid, local_id)
                    else:
                        print('This should never happen. (No country selected.)')
                    imaer_doc.feature_members.append(es)

                # if it is a building layer
                if input_layer['code'] == 'bld':
                    bld = self.get_building_from_gui(feat, geom, crs_dest_srid)
                    imaer_doc.feature_members.append(bld)

                # if it is a calculation point layer
                if input_layer['code'] == 'cp':
                    cp = self.get_calculation_point_from_gui(feat, geom, crs_dest_srid, local_id)
                    imaer_doc.feature_members.append(cp)

        # Custom Time Varying Profile
        if self.checkBox_tvp.isChecked():
            for row in range(self.tableView_tvp.model().rowCount()):
                tvp = self.tvp_model.item(row, 0).data()
                imaer_doc.definitions.append(tvp)

        return imaer_doc

    # Emission Source
    def get_emission_source_from_gui(self, feat, geom, epsg_id, local_id):
        sector_id = self.get_feature_value(self.fcb_es_sector_id, feat)
        label = self.get_feature_value(self.fcb_es_label, feat)
        description = self.get_feature_value(self.fcb_es_description, feat)

        es = EmissionSource(local_id=local_id, sector_id=sector_id, label=label, geom=geom, epsg_id=epsg_id)
        es.description = description

        # emission source characteristics
        if self.groupBox_es_characteristics.isChecked():
            esc_height = self.get_feature_value(self.fcb_es_emission_height, feat)
            esc_spread = self.get_feature_value(self.fcb_es_spread, feat)
            prim_bld = self.get_feature_value(self.fcb_es_prim_bld, feat)

            # heat content
            hc_value = self.get_feature_value(self.fcb_es_hc_value, feat)
            if hc_value is not None:
                hc = SpecifiedHeatContent(value=hc_value)
            else:
                hc = None

            # time varying profile
            tvp = None
            tvp_standard = self.get_feature_value(self.fcb_es_tvp_standard, feat)
            if tvp_standard is not None:
                tvp = StandardTimeVaryingProfile(standard_type=tvp_standard)
            tvp_reference = self.get_feature_value(self.fcb_es_tvp_reference, feat)
            if tvp_reference is not None:
                tvp = ReferenceTimeVaryingProfile(local_id=tvp_reference)

            esc = EmissionSourceCharacteristics(
                building_id=prim_bld,
                emission_height=esc_height,
                spread=esc_spread,
                heat_content=hc,
                time_varying_profile=tvp,
            )
            es.emission_source_characteristics = esc

        # emissions
        es.emissions = []
        em = self.get_feature_value(self.fcb_em_nox, feat)
        if em is not None:
            es.emissions.append(Emission('NOX', em))
        em = self.get_feature_value(self.fcb_em_nh3, feat)
        if em is not None:
            es.emissions.append(Emission('NH3', em))

        return es

    # ADMS Emission Source
    def get_adms_emission_source_from_gui(self, feat, geom, epsg_id, local_id):
        sector_id = self.get_feature_value(self.fcb_es_sector_id, feat)
        label = self.get_feature_value(self.fcb_es_label, feat)
        description = self.get_feature_value(self.fcb_es_description, feat)

        es = EmissionSource(local_id=local_id, sector_id=sector_id, label=label, geom=geom, epsg_id=epsg_id)
        es.description = description

        # emission source characteristics
        if self.groupBox_es_characteristics.isChecked():
            prim_bld = self.get_feature_value(self.fcb_es_prim_bld, feat)
            asc_height = self.get_feature_value(self.fcb_es_adms_height, feat)
            asc_heat_capacity = self.get_feature_value(self.fcb_es_adms_heat_capacity, feat)
            asc_source_type = self.get_feature_value(self.fcb_es_adms_source_type, feat)
            asc_diameter = self.get_feature_value(self.fcb_es_adms_diameter, feat)
            asc_elevation_angle = self.get_feature_value(self.fcb_es_adms_elevation_angle, feat)
            asc_horizontal_angle = self.get_feature_value(self.fcb_es_adms_horizontal_angle, feat)
            asc_width = self.get_feature_value(self.fcb_es_adms_width, feat)
            asc_vertical_dimension = self.get_feature_value(self.fcb_es_adms_vertical_dimension, feat)
            asc_buoyancy_type = self.get_feature_value(self.fcb_es_adms_buoyancy_type, feat)
            asc_density = self.get_feature_value(self.fcb_es_adms_density, feat)
            asc_temperature = self.get_feature_value(self.fcb_es_adms_temperature, feat)
            asc_efflux_type = self.get_feature_value(self.fcb_es_adms_efflux_type, feat)
            asc_vertical_velocity = self.get_feature_value(self.fcb_es_adms_vertical_velocity, feat)
            asc_volumetric_flow_rate = self.get_feature_value(self.fcb_es_adms_volumetric_flow_rate, feat)

            asc = ADMSSourceCharacteristics(
                building_id=prim_bld, height=asc_height, specific_heat_capacity=asc_heat_capacity,
                source_type=asc_source_type, diameter=asc_diameter, elevation_angle=asc_elevation_angle,
                horizontal_angle=asc_horizontal_angle, width=asc_width,
                vertical_dimension=asc_vertical_dimension, buoyancy_type=asc_buoyancy_type,
                density=asc_density, temperature=asc_temperature, efflux_type=asc_efflux_type,
                vertical_velocity=asc_vertical_velocity, volumetric_flow_rate=asc_volumetric_flow_rate
            )

            # time varying profiles
            # hourly
            hourly_tvp = None
            tvp_standard = self.get_feature_value(self.fcb_es_tvp_adms_hourly_standard, feat)
            if tvp_standard is not None:
                hourly_tvp = StandardTimeVaryingProfile(standard_type=tvp_standard)
            tvp_reference = self.get_feature_value(self.fcb_es_tvp_adms_hourly_reference, feat)
            if tvp_reference is not None:
                hourly_tvp = ReferenceTimeVaryingProfile(local_id=tvp_reference)
            asc.hourly_variation = hourly_tvp

            # monthly
            monthly_tvp = None
            tvp_standard = self.get_feature_value(self.fcb_es_tvp_adms_monthly_standard, feat)
            if tvp_standard is not None:
                monthly_tvp = StandardTimeVaryingProfile(standard_type=tvp_standard)
            tvp_reference = self.get_feature_value(self.fcb_es_tvp_adms_monthly_reference, feat)
            if tvp_reference is not None:
                monthly_tvp = ReferenceTimeVaryingProfile(local_id=tvp_reference)
            asc.monthly_variation = monthly_tvp

            es.emission_source_characteristics = asc

        # emissions
        es.emissions = []
        em = self.get_feature_value(self.fcb_em_nox, feat)
        if em is not None:
            es.emissions.append(Emission('NOX', em))
        em = self.get_feature_value(self.fcb_em_nh3, feat)
        if em is not None:
            es.emissions.append(Emission('NH3', em))

        return es

    # SRM2Road
    def get_srm2_road_from_gui(self, feat, geom, epsg_id, local_id):
        sector_id = 3100  # This is the only option in NL
        label = self.get_feature_value(self.fcb_rd_label, feat)

        road_area_type = 'NL'  # This is the only option in NL
        road_type = self.get_feature_value(self.fcb_rd_type, feat)

        es = SRM2Road(
            local_id=local_id,
            sector_id=sector_id,
            label=label,
            geom=geom,
            epsg_id=epsg_id,
            road_area_type=road_area_type,
            road_type=road_type)

        es.description = self.get_feature_value(self.fcb_rd_description, feat)

        es.tunnel_factor = self.get_feature_value(self.fcb_rd_tunnel_factor, feat)
        es.elevation = self.get_feature_value(self.fcb_rd_elevation, feat)
        es.elevation_height = self.get_feature_value(self.fcb_rd_elevation_height, feat)
        es.traffic_direction = self.get_feature_value(self.fcb_rd_traffic_direction, feat)

        # barriers
        for side in ['left', 'right']:
            fcb = getattr(self, f'fcb_rd_b_{side}_type')
            b_type = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_b_{side}_height')
            b_height = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_b_{side}_distance')
            b_distance = self.get_feature_value(fcb, feat)

            if not (b_type is None and b_height is None and b_distance is None):
                rsb = Srm2RoadSideBarrier(b_type, b_height, b_distance)
                if side == 'left':
                    es.barrier_left = rsb
                else:
                    es.barrier_right = rsb

        # vehicles
        vehicles = []
        vehicle_types = {
            'lt1': 'LIGHT_TRAFFIC',
            'lt2': 'LIGHT_TRAFFIC',
            'nf': 'NORMAL_FREIGHT',
            'hf': 'HEAVY_FREIGHT',
            'ab': 'AUTO_BUS'
        }
        for veh_type_key, veh_type_name in vehicle_types.items():

            fcb = getattr(self, f'fcb_rd_v_{veh_type_key}_vehicles_per_time')
            veh_number = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_v_{veh_type_key}_stagnation')
            veh_stagnation = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_v_{veh_type_key}_maxspeed')
            veh_speed = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_v_{veh_type_key}_strict')
            veh_strict = self.get_feature_value(fcb, feat)

            if not (veh_number is None and veh_stagnation is None):
                vehicle = StandardVehicle(
                    vehicles_per_time_unit=veh_number,
                    time_unit='DAY',
                    stagnation_factor=veh_stagnation,
                    vehicle_type=veh_type_name,
                    maximum_speed=veh_speed,
                    strict_enforcement=veh_strict
                )
                vehicles.append(vehicle)

            es.vehicles = vehicles

        return es

    # ADMSRoad
    def get_adms_road_from_gui(self, feat, geom, epsg_id, local_id):
        sector_id = 3100  # This is the only option in UK
        label = self.get_feature_value(self.fcb_rd_label, feat)

        road_area_type = self.get_feature_value(self.fcb_rd_area_type, feat)
        road_type = self.get_feature_value(self.fcb_rd_type, feat)

        es = ADMSRoad(
            local_id=local_id,
            sector_id=sector_id,
            label=label,
            geom=geom,
            epsg_id=epsg_id,
            road_area_type=road_area_type,
            road_type=road_type)

        es.description = self.get_feature_value(self.fcb_rd_description, feat)

        es.width = self.get_feature_value(self.fcb_rd_width, feat)
        es.elevation = self.get_feature_value(self.fcb_rd_elevation, feat)
        es.gradient = self.get_feature_value(self.fcb_rd_gradient, feat)
        es.coverage = self.get_feature_value(self.fcb_rd_coverage, feat)
        es.tunnel_factor = self.get_feature_value(self.fcb_rd_tunnel_factor, feat)
        es.elevation_height = self.get_feature_value(self.fcb_rd_elevation_height, feat)
        es.traffic_direction = self.get_feature_value(self.fcb_rd_traffic_direction, feat)

        # barriers
        for side in ['left', 'right']:
            fcb = getattr(self, f'fcb_rd_b_{side}_type')
            b_type = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_b_{side}_height_av')
            b_height_av = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_b_{side}_height_max')
            b_height_max = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_b_{side}_height_min')
            b_height_min = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_b_{side}_distance')
            b_distance = self.get_feature_value(fcb, feat)
            fcb = getattr(self, f'fcb_rd_b_{side}_porosity')
            b_porosity = self.get_feature_value(fcb, feat)

            if not (b_type is None):
                rsb = AdmsRoadSideBarrier(
                    b_type, b_distance, b_height_av,
                    b_height_max, b_height_min, b_porosity
                )
                if side == 'left':
                    es.barrier_left = rsb
                else:
                    es.barrier_right = rsb

        # time varying profile
        # hourly
        hourly_tvp = None
        tvp_standard = self.get_feature_value(self.fcb_rd_tvp_adms_hourly_standard, feat)
        if tvp_standard is not None:
            hourly_tvp = StandardTimeVaryingProfile(standard_type=tvp_standard)
        tvp_reference = self.get_feature_value(self.fcb_rd_tvp_adms_hourly_reference, feat)
        if tvp_reference is not None:
            hourly_tvp = ReferenceTimeVaryingProfile(local_id=tvp_reference)

        es.hourly_variation = hourly_tvp

        # monthly
        monthly_tvp = None
        tvp_standard = self.get_feature_value(self.fcb_rd_tvp_adms_monthly_standard, feat)
        if tvp_standard is not None:
            monthly_tvp = StandardTimeVaryingProfile(standard_type=tvp_standard)
        tvp_reference = self.get_feature_value(self.fcb_rd_tvp_adms_monthly_reference, feat)
        if tvp_reference is not None:
            monthly_tvp = ReferenceTimeVaryingProfile(local_id=tvp_reference)

        es.monthly_variation = monthly_tvp

        # vehicles
        vehicles = []

        if self.radio_veh_page_eft.isChecked():
            fcb = getattr(self, f'fcb_rd_v_eft_link_speed')
            link_speed = self.get_feature_value(fcb, feat)
            if link_speed is not None:
                link_speed = int(link_speed)

            vehicle_types = {
                'car': 'Car',
                'taxi': 'Tax',
                'motor': 'Mot',
                'lgv': 'LGV',
                'hgv': 'HGV',
                'bus': 'Bus'
            }

            # get the time unit from the gui
            time_unit_ui = self.fcb_rd_v_eft_units.currentText()

            if time_unit_ui == 'p/hour':
                time_unit = 'HOUR'
            elif time_unit_ui == 'p/24 hour':
                time_unit = 'DAY'
            elif time_unit_ui == 'p/month':
                time_unit = 'MONTH'
            elif time_unit_ui == 'p/year':
                time_unit = 'YEAR'
            else:
                time_unit = None

            for veh_type_key, veh_type_name in vehicle_types.items():
                fcb = getattr(self, f'fcb_rd_v_eft_n_{veh_type_key}')
                veh_number = self.get_feature_value(fcb, feat)

                if not (veh_number is None):
                    vehicle = StandardVehicle(
                        vehicles_per_time_unit=veh_number,
                        time_unit=time_unit,
                        stagnation_factor=0.0,
                        vehicle_type=veh_type_name,
                        maximum_speed=link_speed,
                        strict_enforcement='false'
                    )
                    vehicles.append(vehicle)

        # Custom vehicles
        if self.radio_veh_page_custom.isChecked():
            description = self.get_feature_value(self.fcb_rd_v_custom_description, feat)
            movements = self.get_feature_value(self.fcb_rd_v_custom_movements, feat)
            em_nox = self.get_feature_value(self.fcb_rd_v_custom_em_nox, feat)
            em_nh3 = self.get_feature_value(self.fcb_rd_v_custom_em_nh3, feat)

            # get the time unit from the gui
            time_unit_ui = self.fcb_rd_v_custom_movements_units.currentText()

            if time_unit_ui == 'p/hour':
                time_unit = 'HOUR'
            elif time_unit_ui == 'p/24 hour':
                time_unit = 'DAY'
            elif time_unit_ui == 'p/month':
                time_unit = 'MONTH'
            elif time_unit_ui == 'p/year':
                time_unit = 'YEAR'
            else:
                time_unit = None

            emission = []
            if em_nox is not None:
                emission.append(Emission('NOX', em_nox))
            if em_nh3 is not None:
                emission.append(Emission('NH3', em_nh3))

            veh = CustomVehicle(
                vehicles_per_time_unit=movements,
                time_unit=time_unit,
                description=description,
                emissions=emission
            )
            vehicles.append(veh)

        es.vehicles = vehicles
        return es

    # Buildings
    def get_building_from_gui(self, feat, geom, epsg_id):

        bld_id = self.get_feature_value(self.fcb_bld_id, feat)
        bld_hgt = self.get_feature_value(self.fcb_bld_height, feat)
        bld_diameter = self.get_feature_value(self.fcb_bld_diameter, feat)
        bld_label = self.get_feature_value(self.fcb_bld_label, feat)

        b = Building(
            local_id=bld_id,
            height=bld_hgt,
            label=bld_label,
            geom=geom,
            epsg_id=epsg_id,
            diameter=bld_diameter)

        return b

    # CalculationPoints
    def get_calculation_point_from_gui(self, feat, geom, epsg_id, local_id):

        cp_id = self.get_feature_value(self.fcb_cp_id, feat)
        if cp_id is None:
            cp_id = local_id  # fall back to local_id

        country = self.combo_country.currentData()
        if country == 'NL':
            cp = CalculationPoint(local_id=cp_id)
        elif country == 'UK':
            cp = NcaCustomCalculationPoint(local_id=cp_id)
        else:
            return None

        cp.gm_point = geom
        cp.epsg_id = epsg_id
        
        cp.label = self.get_feature_value(self.fcb_cp_label, feat)
        cp.height = self.get_feature_value(self.fcb_cp_height, feat)
        cp.assessment_category = self.get_feature_value(self.fcb_cp_category, feat)
        cp.description = self.get_feature_value(self.fcb_cp_description, feat)
        if country == 'UK':
            cp.road_local_fraction_no2 = self.get_feature_value(self.fcb_cp_local_fraction_no2, feat)
        
        if country == 'UK' and self.group_cp_er.isChecked():
            er = EntityReference()
            er.entity_type = self.get_feature_value(self.fcb_cp_er_type, feat)
            er.description = self.get_feature_value(self.fcb_cp_er_description, feat)

            cl = self.get_feature_value(self.fcb_cp_er_cl_nox, feat)
            if cl is not None:
                er.critical_levels.append(CriticalLevel('CONCENTRATION', 'NOX', cl))
            cl = self.get_feature_value(self.fcb_cp_er_cl_nh3, feat)
            if cl is not None:
                er.critical_levels.append(CriticalLevel('CONCENTRATION', 'NH3', cl))
            cl = self.get_feature_value(self.fcb_cp_er_cl_load, feat)
            if cl is not None:
                er.critical_levels.append(CriticalLevel('DEPOSITION', 'NOXNH3', cl))
        
            cp.entity_reference = er

        return cp

    def open_time_varying_profile_dlg(self, tvp=None):
        self.plugin.log('open_tvp_dlg()', user='dev')
        if self.sender().objectName() == 'button_tvp_add':
            tvp = CustomTimeVaryingProfile(local_id='', label='', custom_type='THREE_DAY', values=[])
            row = None
        else:
            row = self.tableView_tvp.selectionModel().selectedRows()[0].row()
            if self.sender().objectName() == 'button_tvp_delete':
                # No need to open the dialog, just delete the row
                self.tvp_model.removeRow(row)
                return
            tvp = self.tvp_model.item(row, 0).data()
        self.time_varying_profile_dlg.set_by_tvp(tvp)
        self.time_varying_profile_dlg.show()
        result = self.time_varying_profile_dlg.exec_()
        if result:
            tvp = self.time_varying_profile_dlg.get_tvp()
            row = self.add_tvp_to_table(tvp, row)
            self.tableView_tvp.selectRow(row)

    def add_tvp_to_table(self, tvp, row=None):
        local_id_item = QStandardItem(f'{tvp.local_id}')
        local_id_item.setData(tvp)
        label_item = QStandardItem(f'{tvp.label}')
        custom_type_item = QStandardItem(f'{tvp.custom_type}')
        values_item = QStandardItem(f'{len(tvp.values)} values')
        if row is None:
            row = self.tvp_model.rowCount()
        else:
            self.tvp_model.removeRow(row)
        self.tvp_model.insertRow(row, [local_id_item, label_item, custom_type_item, values_item])
        return row

    def get_feature_value(self, widget, feat, cast_to=None):
        if not isinstance(widget, QgsFieldComboBox):
            return None
        field_name = widget.currentField()
        if field_name == '':
            return None
            # return widget_set['fixed'].text() TODO: return fixed value after data type check (or something..)
        else:
            value = feat[field_name]

        if isinstance(value, QVariant) and str(value) == 'NULL':
            return None

        if cast_to is not None:
            if cast_to == 'float':
                if isinstance(result, float):
                    return
                if isInstance(result, QVariant):
                    result.toFloat()
            elif cast_to == 'integer':
                return result.toInt()
            elif cast_to == 'string':
                return result.toString()
        return value

    def save_settings(self):
        work_dir = self.plugin.settings.value('imaer_plugin/work_dir', defaultValue=None)

        if work_dir is None:
            self.plugin.log('Work direction not set.', lvl='Critical', bar=True)
            return

        # TODO: choose file name
        base_name = 'generate_gml_config.json'
        out_fn = os.path.join(work_dir, base_name)
        field_dict = self.collect_settings()
        txt = json.dumps(field_dict, indent=4)
        try:
            with open(out_fn, 'w') as out_file:
                out_file.write(txt)
                self.plugin.log(f'Configuration file saved ({out_fn})', bar=True)
        except:  # For anything that can go wrong here!
            self.plugin.log(f'Could not save configuration file ({out_fn})', lvl='Critical', bar=True)

    def load_settings(self, btn_info=None, in_fn=None):
        if in_fn is None:
            work_dir = self.plugin.settings.value('imaer_plugin/work_dir', defaultValue=None)

            if work_dir is None:
                self.plugin.log('Work directory not set.', lvl='Critical', bar=True)
                return False

            # TODO: choose file name
            base_name = 'generate_gml_config.json'
            in_fn = os.path.join(work_dir, base_name)

        if not os.path.isfile(in_fn):
            self.plugin.log(f'Configuration file not found ({in_fn})', lvl='Warning', bar=True)
            return False

        with open(in_fn, 'r') as out_file:
            txt = out_file.read()

        field_dict = json.loads(txt)

        config_file_version = field_dict.get('imaer_plugin_version', None)
        if config_file_version is None:
            self.plugin.log('This is not a valid field configuration file', lvl='Warning', bar=True)
            return False
        if field_dict['imaer_plugin_version'] != self.plugin.version:
            self.plugin.log(f'Configuration file has different plugin version ({config_file_version} &lt;&gt; {self.plugin.version})', lvl='Critical', bar=True)
            return False

        self.set_settings(field_dict)
        self.plugin.log(f'Configuration file loaded ({in_fn})', bar=True)
        return True

    def collect_settings(self):
        '''Collects a dictionary with all widget_names and field_names for all QgsFieldComboBoxes'''
        result = {}
        result['imaer_plugin_version'] = self.plugin.version
        # options
        result['options'] = {}
        widget_names = ['group_input_es', 'radioButton_es', 'radioButton_rd',
            'checkBox_bld', 'checkBox_cp', 'checkBox_tvp',
            'combo_project_year', 'edit_project_description',
            'group_situation', 'edit_situation_name', 'combo_situation_type',
            'radio_veh_page_custom', 'radio_veh_page_eft', 'fcb_rd_v_eft_units',
            'group_cp_er',
        ]
        for widget_name in widget_names:
            widget = getattr(self, widget_name)
            # print(widget)
            if widget.__class__.__name__ in ['QGroupBox', 'QRadioButton', 'QCheckBox']:
                result['options'][widget_name] = widget.isChecked()
            if widget.__class__.__name__ == 'QComboBox':
                result['options'][widget_name] = widget.currentText()
            if widget.__class__.__name__ == 'QLineEdit':
                result['options'][widget_name] = widget.text()
            if widget.__class__.__name__ == 'QTextEdit':
                result['options'][widget_name] = widget.toPlainText()
        # fields
        result['fields'] = {}
        for fcb in self.findChildren(QgsFieldComboBox):
            k = fcb.objectName()
            v = fcb.currentText()
            if not v == '':
                result['fields'][k] = v

        return result

    def set_settings(self, settings_cfg):
        '''Sets texts from a dictionary with all widget_names and field_names for all QgsFieldComboBoxes'''
        # print(json.dumps(settings_cfg, indent=4))

        # options
        options = settings_cfg.get('options', {})
        for widget_name, v in options.items():
            widget = getattr(self, widget_name)
            if widget.__class__.__name__ in ['QGroupBox', 'QRadioButton', 'QCheckBox']:
                widget.setChecked(v)
            if widget.__class__.__name__ == 'QComboBox':
                widget.setCurrentText(v)
            if widget.__class__.__name__ == 'QLineEdit':
                widget.setText(v)
            if widget.__class__.__name__ == 'QTextEdit':
                widget.setDocument(QTextDocument(v))

        # fields
        for fcb in self.findChildren(QgsFieldComboBox):
            widget_name = fcb.objectName()
            
            # widget name is not in json
            if widget_name not in settings_cfg['fields']:
                fcb.setCurrentIndex(0)  # Make empty
                continue

            # widget     
            new_field = settings_cfg['fields'][widget_name]
            if new_field == '':
                fcb.setCurrentIndex(0)  # Make empty
                continue
            
            # field name not in layer
            if new_field not in fcb.fields().names():
                fcb.setCurrentIndex(0)  # Make empty
                continue

            # set field name
            fcb.setCurrentText(new_field)

    def make_single_part(self, geom):
        '''Returns single part geometry or None if input has more than 1 part'''
        parts = geom.asGeometryCollection()
        if len(parts) == 1:
            result = parts[0]
            # Make sure the type is Point, LineString or Polygon
            if result.wkbType() in [1, 2, 3]:
                return result
        return None
