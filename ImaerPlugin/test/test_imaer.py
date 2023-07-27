import os.path
import sys
import unittest
import yaml
import time

from lxml import etree

import faulthandler
faulthandler.enable()

# Get settings for local dev
with open('test/dev.yml') as file:
    try:
        dev_config = yaml.safe_load(file)
        # print(dev_config)
    except yaml.YAMLError as exc:
        print(exc)

sys.path.append(dev_config['path_qgis_python_folder'])

from qgis.core import *

from imaer5 import *
# from connect import *

_GEOM0 = QgsGeometry.fromWkt('POINT(148458.0 411641.0)')
_GEOM1 = QgsGeometry.fromWkt('LINESTRING((1 0, 2 1, 3 0))')
_GEOM2 = QgsGeometry.fromWkt('MULTIPOLYGON(((1 0, 2 1, 3 0, 2 -1, 1 0)))')
_GEOM3 = QgsGeometry.fromWkt('LINESTRING((311279.0 723504.3, 311262.5 723349.6))')
_GEOM4 = QgsGeometry.fromWkt('POLYGON((1 0, 2 1, 3 0, 2 -1, 1 0))')

# Load IMAER xsd for validation check. (Needs internet connection and can take pretty long.)
xsd_fn = os.path.join('test', 'xsd', 'IMAER_5.1.1.xsd')
xmlschema_doc = etree.parse(xsd_fn)
xmlschema = etree.XMLSchema(xmlschema_doc)


class TestImaer(unittest.TestCase):

    def __init__(self, whatever):
        # print('init')
        unittest.TestCase.__init__(self, whatever)

    def validate_xml_online(self, xml_fn):
        pass
        # connect_base_url = dev_config['connect_base_url']
        # connect_version = dev_config['connect_version']
        # connect_key = dev_config['connect_key']
        # self.aerius_connection = AeriusConnection(None, base_url=connect_base_url, version=connect_version, api_key=connect_key)
        # print(self.aerius_connection)

    def validate_xml_locally(self, xml_fn):
        xml_doc = etree.parse(xml_fn)
        result = xmlschema.validate(xml_doc)
        # result = xsd.validate(xml_fn)
        error = xmlschema.error_log.last_error
        if error is not None:
            print(error)
        return result

    def generate_gml_file(self, fcc, name):
        output_fn = os.path.join('test', 'output', f'output_{name}.gml')
        fcc.to_xml_file(output_fn)

        validation_result = self.validate_xml_locally(output_fn)
        self.assertTrue(validation_result)

    def test_ffc_empty(self):
        fcc = ImaerDocument()
        self.generate_gml_file(fcc, 'empty')

    def test_ffc_metadata(self):
        fcc = ImaerDocument()
        fcc.metadata = AeriusCalculatorMetadata(
            project={'year': 2020, 'description': 'Some description...'},
            situation={'name': 'Situation 1', 'reference': 'ABCDE12345', 'type': 'PROPOSED'},
            calculation = {'type':'NATURE_AREA', 'substances':['NH3', 'NOX'], 'result_type':'DEPOSITION'},
            version={'aeriusVersion': '2019A_20200610_3aefc4c15b', 'databaseVersion': '2019A_20200610_3aefc4c15b'}
        )
        self.generate_gml_file(fcc, 'metadata')

    def test_ffc_emission_simple(self):
        fcc = ImaerDocument()
        es = EmissionSource(local_id=123, sector_id=9000, label='Bron 123', geom=_GEOM0, epsg_id=28992)
        es.emissions.append(Emission('NH3', 1))
        fcc.feature_members.append(es)
        self.generate_gml_file(fcc, 'em_simple')

    def test_ffc_emission_characteristics01(self):
        hc = SpecifiedHeatContent(value=12.5)
        es = EmissionSource(local_id=1234, sector_id=9999, label='Bron 1234', geom=_GEOM1, epsg_id=28992)
        dv = StandardDiurnalVariation(standard_type='LIGHT_DUTY_VEHICLES')
        es.emission_source_characteristics = EmissionSourceCharacteristics(heat_content=hc, emission_height=2.4, spread=3, diurnal_variation=dv)
        es.emissions.append(Emission('NH3', 4.3))
        es.emissions.append(Emission('NOX', 4.4))
        fcc = ImaerDocument()
        fcc.feature_members.append(es)
        self.generate_gml_file(fcc, 'em_char_01')

    def test_ffc_emission_characteristics02(self):
        fcc = ImaerDocument()
        hc = SpecifiedHeatContent(value=12.5)
        es = EmissionSource(local_id=125, sector_id=9999, label='Bron 125', geom=_GEOM1, epsg_id=28992)
        rdv = ReferenceDiurnalVariation(local_id=125)
        cdv = CustomDiurnalVariation(local_id=125, label='Test label', custom_type='DAY', values=[150, 50]*12)
        fcc.definitions.append(cdv)
        es.emission_source_characteristics = EmissionSourceCharacteristics(heat_content=hc, emission_height=2.4, spread=3, diurnal_variation=rdv)
        es.emissions.append(Emission('NH3', 5))
        es.emissions.append(Emission('NOX', 5.22))
        fcc.feature_members.append(es)
        self.generate_gml_file(fcc, 'em_char_02')

    def test_create_srm2road(self):
        v1 = StandardVehicle(vehicles_per_time_unit=333,
                             time_unit='DAY',
                             vehicle_type='Bus',
                             maximum_speed=33,
                             strict_enforcement='false',
                             stagnation_factor=0.0)
        es = SRM2Road(
            local_id=33,
            sector_id='3100',
            label='testlabel',
            geom=_GEOM1,
            epsg_id=28992,
            road_area_type='NL',
            road_type='FREEWAY',
            vehicles=[v1])
        fcc = ImaerDocument()
        fcc.feature_members.append(es)
        self.generate_gml_file(fcc, 'srm2road')

    def test_create_adms_road(self):
        # setup the barrier (left)
        b1 = AdmsRoadSideBarrier(type='BRICK_WALL',
                                 distance=5,
                                 Avheight=7,
                                 Maxheight=10,
                                 Minheight=3,
                                 porosity=5)

        # this is creating the Emissions Source Type (including left barrier)
        es = ADMSRoad(
            local_id=33,
            sector_id='3100',
            label='testlabel',
            geom=_GEOM3,
            epsg_id=27700,
            road_area_type='Sco',
            road_type='Urb',
            elevation=2,
            gradient=0.5,
            width=8,
            coverage=0,
            barrier_left=b1)

        # want to create ADMS road vehicle info (standard vehicle)
        v1 = StandardVehicle(vehicles_per_time_unit=1000,
                             time_unit='DAY',
                             vehicle_type='Bus',
                             maximum_speed=50,
                             strict_enforcement='false',
                             stagnation_factor=0.0)
        # add the vehicle created above to the emission source
        es.vehicles.append(v1)

        em = Emission('NOX', 111)

        # also create ADMS road vehicle info (custom vehicle)
        v2 = CustomVehicle(
            vehicles_per_time_unit=1000,
            time_unit='DAY',
            description='Test test ...',
            emission=[em]
        )
        es.vehicles.append(v2)

        fcc = ImaerDocument()
        fcc.feature_members.append(es)

        self.generate_gml_file(fcc, 'admsroad')

    def test_create_buildings(self):
        b1 = Building(
            local_id='123',
            height=12.3,
            diameter=1.23,
            label='building no. 123',
            geom=_GEOM0,
            epsg_id=28992)
        b2 = Building(
            local_id='555',
            height=55.5,
            diameter=55,
            label='building no. 555',
            geom=_GEOM4,
            epsg_id=28992)
        fcc = ImaerDocument()
        fcc.feature_members.append(b1)
        fcc.feature_members.append(b2)
        self.generate_gml_file(fcc, 'buildings')

    def test_create_emission_with_building(self):
        building_id = '555'
        es = EmissionSource(local_id=444, sector_id=9000, label='Bron 444', geom=_GEOM0, epsg_id=28992)
        hc = SpecifiedHeatContent(value=4)
        es.emission_source_characteristics = EmissionSourceCharacteristics(heat_content=hc, emission_height=5, building=building_id)
        es.emissions.append(Emission('NOX', 10))
        b = Building(
            local_id=building_id,
            height=55.5,
            label='building no. 555',
            geom=_GEOM4,
            epsg_id=28992)
        fcc = ImaerDocument()
        fcc.feature_members.append(es)
        fcc.feature_members.append(b)
        self.generate_gml_file(fcc, 'emission_with_building')

    def test_create_calculation_points(self):
        cp = CalculationPoint(
            local_id = 888,
            geom = _GEOM0,
            epsg_id=28992,
            label='Pnt 888',
            description='Point number 888.'
        )
        fcc = ImaerDocument()
        fcc.feature_members.append(cp)
        self.generate_gml_file(fcc, 'calculation_points')
