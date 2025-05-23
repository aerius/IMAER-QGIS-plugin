# -*- coding: utf-8 -*-
import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import (
    QVariant,
    QStandardPaths,
    Qt
)
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFileDialog
)

from qgis.core import QgsApplication

from ImaerPlugin.config import ui_settings


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'configuration_dlg.ui'))


class ConfigurationDialog(QDialog, FORM_CLASS):

    def __init__(self, plugin, parent=None):
        super(ConfigurationDialog, self).__init__(parent)

        self.setupUi(self)
        self.plugin = plugin
        self.iface = plugin.iface

        self.init_default_values()
        self.init_gui()

        # Load and save settings once to make sure everything is up to date.
        self.load_ui_from_settings()
        self.save_ui_to_settings()

    def init_gui(self):
        self.label_country.setToolTip('Select the country from the drop down menu')
        self.label_crs.setToolTip('Select the crs from the drop down menu')
        self.label_work_dir.setToolTip('Add path to working directory to save files')
        self.label_connect_server.setToolTip('Add url to connect server e.g. https://connect.aerius.nl/api')
        self.label_connect_ver.setToolTip('Select the version of Connect from the dropdown menu')
        self.label_email.setToolTip('Enter the email address registered the Connect server')
        self.label_key.setToolTip('Enter your api key for the Connect server')
        self.combo_country.addItems([''] + ui_settings['countries'])
        self.combo_crs.addItem('')
        for crs in ui_settings['crs']:
            crs_name = f"{crs['name']} ({crs['srid']})"
            self.combo_crs.addItem(crs_name, crs['srid'])
        self.combo_connect_ver.addItems(ui_settings['supported_connect_versions'])
        self.file_dialog = QFileDialog()
        self.button_get_key.clicked.connect(self.get_api_key)
        self.button_browse_work_dir.clicked.connect(self.browse_work_dir)
        self.combo_country.currentTextChanged.connect(self.update_all_widgets)

    def init_default_values(self):
        work_dir_setting = self.plugin.settings.value('imaer_plugin/work_dir', defaultValue=None)
        if work_dir_setting is None:
            work_dir_setting = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
            self.plugin.settings.setValue('imaer_plugin/work_dir', work_dir_setting)

        connect_base_url = self.plugin.settings.value('imaer_plugin/connect_base_url', defaultValue=None)
        if connect_base_url is None:
            default_base_url = self.plugin.aerius_connection.default_base_url
            self.plugin.settings.setValue('imaer_plugin/connect_base_url', default_base_url)
            default_version = self.plugin.aerius_connection.default_version
            self.plugin.settings.setValue('imaer_plugin/connect_version', default_version)

    def load_ui_from_settings(self):
        country_setting = self.plugin.settings.value('imaer_plugin/country', defaultValue='')
        self.combo_country.setCurrentText(country_setting)

        crs_setting = self.plugin.settings.value('imaer_plugin/crs', defaultValue='')
        crs_index = self.combo_crs.findData(crs_setting)
        if crs_index == -1:  # not found
            crs_idex = 0
        self.combo_crs.setCurrentIndex(crs_index)

        work_dir_setting = self.plugin.settings.value('imaer_plugin/work_dir', defaultValue='')
        self.edit_work_dir.setText(work_dir_setting)

        connect_server_setting = self.plugin.settings.value('imaer_plugin/connect_base_url', defaultValue='')
        self.edit_connect_base_url.setText(connect_server_setting)

        connect_version_setting = self.plugin.settings.value('imaer_plugin/connect_version', defaultValue='')
        self.combo_connect_ver.setCurrentText(connect_version_setting)

        email_setting = self.plugin.settings.value('imaer_plugin/connect_email', defaultValue='')
        self.edit_email.setText(email_setting)

        key_setting = self.plugin.settings.value('imaer_plugin/connect_key', defaultValue='')
        self.edit_key.setText(key_setting)

    def save_ui_to_settings(self):
        self.plugin.settings.setValue('imaer_plugin/country', self.combo_country.currentText())
        self.plugin.settings.setValue('imaer_plugin/crs', self.combo_crs.currentData())
        self.plugin.settings.setValue('imaer_plugin/work_dir', self.edit_work_dir.text())
        self.plugin.settings.setValue('imaer_plugin/connect_base_url', self.edit_connect_base_url.text())
        self.plugin.settings.setValue('imaer_plugin/connect_version', self.combo_connect_ver.currentText())
        self.plugin.settings.setValue('imaer_plugin/connect_email', self.edit_email.text())
        self.plugin.settings.setValue('imaer_plugin/connect_key', self.edit_key.text())
        
        country = self.combo_country.currentText()
        if country in ui_settings['connect_countries']:
            self.plugin.aerius_connection.base_url = self.edit_connect_base_url.text()
            self.plugin.aerius_connection.version = self.combo_connect_ver.currentText()
            self.plugin.aerius_connection.api_key = self.edit_key.text()
            # self.plugin.aerius_connection.check_connection()
            self.plugin.connect_jobs_dlg.update_combo_calculation_type()
        else:
            self.plugin.aerius_connection.base_url = None
            self.plugin.aerius_connection.version = None
        self.plugin.generate_calc_input_dlg.update_emission_tab()

    def update_all_widgets(self):
        country = self.combo_country.currentText()
        if country in ui_settings['connect_countries']:
            self.groupBox_connect.setEnabled(True)
        else:
            self.groupBox_connect.setEnabled(False)

    def get_api_key(self):
        email = self.edit_email.text()

        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        result = self.plugin.aerius_connection.generate_api_key(email)
        QgsApplication.restoreOverrideCursor()

        if result:
            self.edit_key.setText('')
            self.plugin.settings.setValue('imaer_plugin/connect_key', '')
            self.plugin.log('Requested new Connect API key', bar=True)
        else:
            self.plugin.log('Requesting new Connect API key failed', lvl='Critical', bar=True)

    def browse_work_dir(self):
        current_work_dir = self.edit_work_dir.text()
        self.file_dialog.setDirectory(current_work_dir)
        new_dir = self.file_dialog.getExistingDirectory(caption='Select work directory', parent=self)
        self.edit_work_dir.setText(new_dir)
