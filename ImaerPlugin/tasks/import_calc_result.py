import os

from qgis.PyQt.QtCore import QVariant, QFile
from qgis.core import (
    Qgis,
    QgsTask,
    QgsMessageLog,
    QgsProviderRegistry,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsFeature,
    QgsGeometry,
    QgsVectorLayer,
    QgsExpressionContextUtils,
)

# from .. task_timer import TaskTimer
from ImaerPlugin.imaer6 import ImaerDocument
from ImaerPlugin.gpkg import ImaerGpkg
from ImaerPlugin.config import ui_settings
from ImaerPlugin.version import VersionNumber


class ImportImaerCalculatorResultTask(QgsTask):

    def __init__(self, plugin, gml_fn, gpkg_fn, result_callback):
        super().__init__('Import IMAER Calculator Result', QgsTask.CanCancel)
        self.gml_fn = gml_fn
        self.gpkg_fn = gpkg_fn
        self.result = {'status': 'error', 'message': ''}
        self.result_callback = result_callback
        self.plugin = plugin
        self.do_log = True

    def run(self):
        self.log('Started task "{}"'.format(self.description()))
        self.log(f'source: {self.gml_fn}')
        self.log(f'target: {self.gpkg_fn}')

        self.setProgress(1)  # Cause setting to 0% does not work.

        doc = ImaerDocument()
        doc.from_xml_file(self.gml_fn)
        # self.log(f'doc: {str(doc)}')

        self.setProgress(40)

        if os.path.isfile(self.gpkg_fn):
            os.remove(self.gpkg_fn)

        doc_version = VersionNumber(doc.get_version().to_string())
        doc_version_str = doc_version.to_string(2)
        # self.log(doc_version_str)
        if doc_version_str not in ui_settings['supported_imaer_versions']:
            self.result['status'] = 'error'
            self.result['message'] = f'Unsupported IMAER version ({doc.get_version().to_string()}).'
            return False

        member_info = doc.get_member_count()
        result_member_count = 0
        for k, v in member_info.items():
            if k in ['ReceptorPoint', 'SubPoint', 'CalculationPoint']:
                result_member_count += v
        # self.log(result_member_count)

        if result_member_count == 0:
            self.result['status'] = 'warning'
            self.result['message'] = 'No result features found in GML file.'
            return False

        gpkg = ImaerGpkg(self.gpkg_fn, plugin=self.plugin)
        # self.log(str(gpkg))

        # metadata
        gpkg.set_metadata('gml_fn', doc.gml_fn)
        gpkg.set_metadata('imaer_version', doc.get_version().to_string())

        if doc.metadata is None:
            situation_name = ''
        elif doc.metadata.situation is None:
            situation_name = ''
        elif 'name' in doc.metadata.situation:
            situation_name = doc.metadata.situation['name']
        else:
            situation_name = ''
        gpkg.set_metadata('situation_name', situation_name)

        # self.log(gpkg.get_all_metadata())

        receptor_points_layer = None
        receptor_hexagons_layer = None
        sub_points_layer = None
        calculation_points_layer = None

        member_cnt = 0

        for member in doc.feature_members:
            # self.log(member.__class__.__name__)
            if member.__class__.__name__ == 'ReceptorPoint':
                if receptor_points_layer is None:
                    epsg_id = int(member.gm_point.epsg_id)
                    gpkg.create_layer_receptor_points(epsg_id)
                    receptor_points_layer = QgsVectorLayer(f'{self.gpkg_fn}|layername=receptor_points', 'receptor_points', 'ogr')
                    receptor_points_layer.startEditing()
                if receptor_hexagons_layer is None:
                    epsg_id = int(member.representation.epsg_id)
                    gpkg.create_layer_receptor_hexagons(epsg_id)
                    receptor_hexagons_layer = QgsVectorLayer(f'{self.gpkg_fn}|layername=receptor_hexagons', 'receptor_hexagons', 'ogr')
                    receptor_hexagons_layer.startEditing()

                feat = member.to_point_feature()
                receptor_points_layer.addFeature(feat)

                feat = member.to_polygon_feature()
                receptor_hexagons_layer.addFeature(feat)

                member_cnt += 1
            elif member.__class__.__name__ == 'SubPoint':
                if sub_points_layer is None:
                    epsg_id = int(member.gm_point.epsg_id)
                    gpkg.create_layer_sub_points(epsg_id)
                    sub_points_layer = QgsVectorLayer(f'{self.gpkg_fn}|layername=sub_points', 'sub_points', 'ogr')
                    sub_points_layer.startEditing()
                feat = member.to_point_feature()
                sub_points_layer.addFeature(feat)
                member_cnt += 1

            elif member.__class__.__name__ == 'CalculationPoint':
                if calculation_points_layer is None:
                    epsg_id = int(member.gm_point.epsg_id)
                    gpkg.create_layer_calculation_points(epsg_id)
                    calculation_points_layer = QgsVectorLayer(f'{self.gpkg_fn}|layername=calculation_points', 'calcultion_points', 'ogr')
                    calculation_points_layer.startEditing()
                feat = member.to_point_feature()
                calculation_points_layer.addFeature(feat)
                member_cnt += 1

        self.setProgress(80)

        if receptor_points_layer is not None:
            receptor_points_layer.commitChanges()
        if receptor_hexagons_layer is not None:
            receptor_hexagons_layer.commitChanges()
        if sub_points_layer is not None:
            sub_points_layer.commitChanges()
        if calculation_points_layer is not None:
            calculation_points_layer.commitChanges()

        self.setProgress(100)

        self.result['status'] = 'ok'
        return True

    def finished(self, result):
        # self.log('finished task')
        # self.log('FINISHED')
        self.result_callback(self.result, self.gpkg_fn)

    def cancel(self):
        self.result['message'] = 'Task "{name}" was canceled'.format(name=self.description())
        self.log(self.result['message']
        )
        # TODO delete gpkg file
        super().cancel()

    def log(self, message, tab='IMAER Plugin'):
        if self.do_log:
            QgsMessageLog.logMessage(repr(message), tab, level=Qgis.Info)
