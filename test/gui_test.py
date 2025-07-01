import os

plugin = qgis.utils.plugins['ImaerPlugin']

def get_configuration():
    country = plugin.configuration_dlg.combo_country.currentText()
    crs = plugin.configuration_dlg.combo_crs.currentIndex()
    work_dir = plugin.configuration_dlg.edit_work_dir.text()
    return (country, crs, work_dir)

def set_configuration(country=None, crs=None, work_dir=None):
    if country is not None:
        plugin.configuration_dlg.combo_country.setCurrentText(country)
    if crs is not None:
        plugin.configuration_dlg.combo_crs.setCurrentIndex(crs)
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

def remove_tvps():
    plugin.generate_calc_input_dlg.tvp_model.clear()

def add_tvps():
    remove_tvps()

    #tvp 1
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.lineEdit_id.setText('1')
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.lineEdit_label.setText('Een')
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.combo_custom_type.setCurrentText('THREE_DAY')
    csv = '1.0,0.9,1.2\n1.0,1.1,0.8\n' * 12
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.plainTextEdit_csv.setPlainText(csv)
    tvp = plugin.generate_calc_input_dlg.time_varying_profile_dlg.get_tvp()
    plugin.generate_calc_input_dlg.add_tvp_to_table(tvp)

    #tvp 2
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.lineEdit_id.setText('2')
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.lineEdit_label.setText('Twee')
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.combo_custom_type.setCurrentText('MONTHLY')
    csv = '0.12\n1.08\n2.04\n0.6\n1.2\n0.12\n1.08\n0.48\n0.96\n1.92\n1.08\n1.32\n'
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.plainTextEdit_csv.setPlainText(csv)
    tvp = plugin.generate_calc_input_dlg.time_varying_profile_dlg.get_tvp()
    plugin.generate_calc_input_dlg.add_tvp_to_table(tvp)

    #tvp 3
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.lineEdit_id.setText('3')
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.lineEdit_label.setText('Drie')
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.combo_custom_type.setCurrentText('THREE_DAY')
    csv = '''0.9,1.0,1.0
    0.9,1.0,1.0
    0.9,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.1,1.0,1.0
    1.1,1.0,1.0
    1.2,1.0,1.0
    1.1,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    1.0,1.0,1.0
    0.9,1.0,1.0
    0.9,1.0,1.0'''
    plugin.generate_calc_input_dlg.time_varying_profile_dlg.plainTextEdit_csv.setPlainText(csv)
    tvp = plugin.generate_calc_input_dlg.time_varying_profile_dlg.get_tvp()
    plugin.generate_calc_input_dlg.add_tvp_to_table(tvp)

# Generate GML

def generate_gml_uk_roads(delete_layers=True):
    set_configuration(country='UK', crs=2, work_dir=test_work_dir)

    fn = os.path.join(test_input_dir, 'test_input_uk.gpkg')
    ln = 'Traffic_shapefile_UK_27700'
    layer_roads = QgsVectorLayer(f'{fn}|layername={ln}', f'test_{ln}')
    QgsProject.instance().addMapLayer(layer_roads)
    plugin.generate_calc_input_dlg.combo_layer_rd.setLayer(layer_roads)

    cfg_fn = os.path.join(test_input_dir, 'generate_gml_config_uk_roads.json')
    load_configuration_file(cfg_fn)

    gml_fn = os.path.join(test_work_dir, 'test_uk_roads.gml')
    plugin.generate_calc_input_dlg.edit_outfile.setText(gml_fn)
    plugin.generate_calc_input_dlg.generate_imaer_gml()

    if delete_layers:
        QgsProject.instance().removeMapLayers([layer_roads.id()])

def generate_gml_uk_points_buildings(delete_layers=True):
    # uk generic and buildings
    set_configuration(country='UK', crs=2, work_dir=test_work_dir)
    fn = os.path.join(test_input_dir, 'test_input_uk.gpkg')

    ln = 'generic_points_uk'
    layer_points = QgsVectorLayer(f'{fn}|layername={ln}', f'test_{ln}')
    QgsProject.instance().addMapLayer(layer_points)
    plugin.generate_calc_input_dlg.combo_layer_es.setLayer(layer_points)

    ln = 'buildings_polygon_uk'
    layer_buildings = QgsVectorLayer(f'{fn}|layername={ln}', f'test_{ln}')
    QgsProject.instance().addMapLayer(layer_buildings)
    plugin.generate_calc_input_dlg.combo_layer_bld.setLayer(layer_buildings)

    cfg_fn = os.path.join(test_input_dir, 'generate_gml_config_uk_points_buildings.json')
    load_configuration_file(cfg_fn)

    gml_fn = os.path.join(test_work_dir, f'test_uk_{ln}.gml')
    plugin.generate_calc_input_dlg.edit_outfile.setText(gml_fn)
    plugin.generate_calc_input_dlg.generate_imaer_gml()

    if delete_layers:
        QgsProject.instance().removeMapLayers([layer_points.id(), layer_buildings.id()])

def generate_gml_uk_calculation_points(delete_layers=True):
    # uk calculation_points
    set_configuration(country='UK', crs=2, work_dir=test_work_dir)
    fn = os.path.join(test_input_dir, 'test_input_uk.gpkg')
    ln = 'calculation_points'

    layer_points = QgsVectorLayer(f'{fn}|layername={ln}', f'test_{ln}')
    QgsProject.instance().addMapLayer(layer_points)
    plugin.generate_calc_input_dlg.combo_layer_es.setLayer(layer_points)

    cfg_fn = os.path.join(test_input_dir, f'generate_gml_config_uk_{ln}.json')
    load_configuration_file(cfg_fn)

    gml_fn = os.path.join(test_work_dir, f'test_uk_{ln}.gml')
    plugin.generate_calc_input_dlg.edit_outfile.setText(gml_fn)
    plugin.generate_calc_input_dlg.generate_imaer_gml()

    if delete_layers:
        QgsProject.instance().removeMapLayers([layer_points.id()])

def generate_gml_uk_points_tvp(delete_layers=True):
    # uk generic and time varying profiles
    set_configuration(country='UK', crs=2, work_dir=test_work_dir)
    fn = os.path.join(test_input_dir, 'test_input_uk.gpkg')

    ln = 'generic_points_uk'
    layer_points = QgsVectorLayer(f'{fn}|layername={ln}', f'test_{ln}')
    QgsProject.instance().addMapLayer(layer_points)
    plugin.generate_calc_input_dlg.combo_layer_es.setLayer(layer_points)

    cfg_fn = os.path.join(test_input_dir, 'generate_gml_config_uk_points_tvp.json')
    load_configuration_file(cfg_fn)

    gml_fn = os.path.join(test_work_dir, f'test_uk_{ln}.gml')
    plugin.generate_calc_input_dlg.edit_outfile.setText(gml_fn)
    plugin.generate_calc_input_dlg.generate_imaer_gml()

    if delete_layers:
        QgsProject.instance().removeMapLayers([layer_points.id()])


test_dir = os.path.dirname(__file__)
# print(test_dir)
plugin_dir = os.path.dirname(test_dir)
# print(plugin_dir)

user_config = get_configuration()
print('current user config:', user_config)

test_input_dir = os.path.join(test_dir, 'input')
# print(test_input_dir)

test_work_dir = os.path.join(QDir.tempPath(), 'imaer_plugin_gui_test')
if not os.path.exists(test_work_dir):
    os.makedirs(test_work_dir)
# print(test_work_dir)

delete_layers = True

# run tests
add_tvps()

generate_gml_uk_roads(delete_layers)
generate_gml_uk_points_buildings(delete_layers)
generate_gml_uk_calculation_points(delete_layers)
generate_gml_uk_points_tvp(delete_layers)

remove_tvps()

# restore configuration
set_configuration(*user_config)

print('Done')
