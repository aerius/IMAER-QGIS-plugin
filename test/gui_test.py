import os

demo_data_dir = '/home/raymond/git/AERIUS-QGIS-plugins/demodata/'
old_work_dir = '/home/raymond/imaer_plugin'

work_dir = os.path.join(QDir.tempPath(), 'imaer_plugin_gui_test')
if not os.path.exists(work_dir):
        os.makedirs(work_dir)

plugin = qgis.utils.plugins['ImaerPlugin']

# Settings
def set_configuration(country=None, crs=None, work_dir=None):
    if country is not None:
        plugin.configuration_dlg.combo_country.setCurrentText(country)
    if crs is not None:
        crs_dict = {28992: 1, 27700: 2}
        plugin.configuration_dlg.combo_crs.setCurrentIndex(crs_dict[crs])
    if work_dir is not None:
        plugin.configuration_dlg.edit_work_dir.setText(work_dir)
    
    plugin.configuration_dlg.save_ui_to_settings()
    plugin.aerius_connection.check_connection()
    plugin.update_connect_widgets()
    plugin.update_crs_widgets()

def load_configuration_file(cfg_fn):
    print(f'Loading: {cfg_fn}')
    result = plugin.generate_calc_input_dlg.load_settings(in_fn=cfg_fn)
    if result is False:
        print(f'Could not load configuration file ({cfg_fn})')

set_configuration(country='NL', crs=28992, work_dir=work_dir)
#plugin.configuration_dlg.show()
set_configuration(country='UK', crs=27700)

# Generate GML

# uk roads
fn = os.path.join(demo_data_dir, 'test_input_uk.gpkg')
ln = 'Traffic_shapefile_UK_27700'
layer_roads = QgsVectorLayer(f'{fn}|layername={ln}', 'test_input_uk_roads')
QgsProject.instance().addMapLayer(layer_roads)
plugin.generate_calc_input_dlg.combo_layer_rd.setLayer(layer_roads)

cfg_fn = os.path.join(demo_data_dir, 'generate_gml_config_uk_roads.json')
load_configuration_file(cfg_fn)

gml_fn = os.path.join(work_dir, 'test_uk_roads.gml')
plugin.generate_calc_input_dlg.edit_outfile.setText(gml_fn)
plugin.generate_calc_input_dlg.generate_imaer_gml()

QgsProject.instance().removeMapLayers([layer_roads.id()])

# uk generic and buildings

fn = os.path.join(demo_data_dir, 'test_input_uk.gpkg')

ln = 'generic_points_uk'
layer_points = QgsVectorLayer(f'{fn}|layername={ln}', 'test_input_points')
QgsProject.instance().addMapLayer(layer_points)
plugin.generate_calc_input_dlg.combo_layer_es.setLayer(layer_points)

ln = 'buildings_polygon_uk'
layer_buildings = QgsVectorLayer(f'{fn}|layername={ln}', 'test_input_buildings')
QgsProject.instance().addMapLayer(layer_buildings)
plugin.generate_calc_input_dlg.combo_layer_bld.setLayer(layer_buildings)

cfg_fn = os.path.join(demo_data_dir, 'generate_gml_config_uk_points.json')
load_configuration_file(cfg_fn)

gml_fn = os.path.join(work_dir, 'test_uk_points.gml')
plugin.generate_calc_input_dlg.edit_outfile.setText(gml_fn)
plugin.generate_calc_input_dlg.generate_imaer_gml()

QgsProject.instance().removeMapLayers([layer_points.id()])
QgsProject.instance().removeMapLayers([layer_buildings.id()])


set_configuration(work_dir=old_work_dir)
