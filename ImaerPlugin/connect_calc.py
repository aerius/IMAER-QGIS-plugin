# -*- coding: utf-8 -*-
import os

from PyQt5.QtWidgets import (
    QDialog
)
from PyQt5 import uic

from .connect import (
    AeriusConnection
)


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'connect_calc_dlg.ui'))




class ConnectCalcDialog(QDialog, FORM_CLASS):

    def __init__(self, plugin, parent=None):
        super(ConnectCalcDialog, self).__init__(parent)

        self.setupUi(self)
        self.plugin = plugin
        self.iface = plugin.iface
        api_key = self.plugin.settings.value('variables/imaer_plugin_connect_key', defaultValue='')
        self.connection = AeriusConnection(api_key=api_key)

        self.init_gui()


    def init_gui(self):
        self.button_validate.clicked.connect(self.validate)


    def __del__(self):
        self.button_validate.clicked.disconnect(self.validate)


    '''def load_ui_from_settings(self):
        print('load_ui_from_settings')

        email_setting = self.plugin.settings.value('variables/imaer_plugin_connect_email', defaultValue='@@@')
        print(email_setting)
        self.edit_email.setText(email_setting)

        key_setting = self.plugin.settings.value('variables/imaer_plugin_connect_key', defaultValue='kkk')
        print(key_setting)
        self.edit_key.setText(key_setting)


    def save_ui_to_settings(self):
        self.plugin.settings.setValue('variables/imaer_plugin_connect_email', self.edit_email.text())
        self.plugin.settings.setValue('variables/imaer_plugin_connect_key', self.edit_key.text())'''


    def validate(self):
        print(self.connection)
        gml_fn = self.edit_gml_input.text()
        print(gml_fn)

        result = self.connection.validate(gml_fn)

        if result['successful']:
            print('GML file is valid')
        else:
            print('GML is NOT valid:')
            for line in result['errors']:
                print('  {}'.format(line['message']))
