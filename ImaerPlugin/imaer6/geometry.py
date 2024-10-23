import sys

from PyQt5.QtXml import QDomDocument

from qgis.core import QgsPoint, QgsLineString, QgsPolygon

# path_qgis_python_folder = "/home/raymond/programs/qgis/qgis-master/share/qgis/python/"
# sys.path.append(path_qgis_python_folder)
# from qgis.core import QgsGeometry


class GmlGeometry():

    def __init__(self, epsg_id=None, gml_id=None):
        self.epsg_id = epsg_id
        self.gml_id = gml_id

    def __str__(self):
        return f'Geometry[{self.geom}, {self.epsg_id, self.gml_id}]'

    def from_xml_reader(self, xml_reader):
        if not xml_reader.isStartElement():
            return
        attributes = xml_reader.attributes()
        if attributes.hasAttribute('srsName'):
            srs_name = attributes.value('srsName')
            self.epsg_id = srs_name.split(':')[-1]
        if attributes.hasAttribute('gml:id'):
            self.gml_id = attributes.value('gml:id')

    def is_valid(self):
        return True


class GmlPoint(GmlGeometry):

    def __init__(self, *, x=None, y=None):
        super().__init__()
        self.x = x
        self.y = y

    def __str__(self):
        return f'GmlPoint[{self.epsg_id}, {self.gml_id}, {self.x:.3f}, {self.y:.3f}]'

    def to_xml_elem(self, doc):
        result = doc.createElement(f'gml:Point')
        result.setAttribute('srsName', f'urn:ogc:def:crs:EPSG::{self.epsg_id}')
        result.setAttribute('gml:id', self.gml_id)

        pos_elem = doc.createElement(f'gml:pos')
        pos_elem.appendChild(doc.createTextNode(f'{self.x} {self.y}'))
        result.appendChild(pos_elem)

        return result

    def from_xml_reader(self, xml_reader):
        super().from_xml_reader(xml_reader)

        start_name = xml_reader.name()
        if start_name == 'Point':
            xml_reader.readNextStartElement()
            if xml_reader.name() == 'pos':
                xml_reader.readNext()
                coords = xml_reader.text()
                parts = coords.split()
                self.x = float(parts[0])
                self.y = float(parts[1])

    def to_geometry(self):
        return QgsPoint(round(self.x, 3), round(self.y, 3))


class GmlLineString(GmlGeometry):  # NEVER TESTED!!!

    def __init__(self, *, coords=None):
        super().__init__()
        self.coords = coords or []

    def __str__(self):
        return f'GmlLineString[{self.epsg_id}, {self.gml_id}, {len(self.coords)}, {self.coords[:4]}]'

    def from_xml_reader(self, xml_reader):
        super().from_xml_reader(xml_reader)

        start_name = xml_reader.name()
        if start_name == 'LineString':
            xml_reader.readNextStartElement()
            if xml_reader.name() == 'posList':
                xml_reader.readNext()
                coords = xml_reader.text()
                print(coords)
                parts = coords.split()
                for part in parts:
                    self.coords.append(float(part))


class GmlPolygon(GmlGeometry):

    def __init__(self, *, epsg_id=None, gml_id=None, exterior=None):
        super().__init__(epsg_id=epsg_id, gml_id=gml_id)
        self.exterior = exterior or []

    def __str__(self):
        return f'GmlPolygon[{self.epsg_id}, {self.gml_id}, {len(self.exterior)}, {self.exterior[:4]}]'

    def to_xml_elem(self, doc):
        result = doc.createElement(f'gml:Polygon')
        result.setAttribute('srsName', f'urn:ogc:def:crs:EPSG::{self.epsg_id}')
        result.setAttribute('gml:id', self.gml_id)

        exterior_elem = doc.createElement(f'gml:exterior')
        pos_elem = doc.createElement(f'gml:pos')

        coords = [str(value) for value in self.exterior]
        pos_elem.appendChild(doc.createTextNode(' '.join(coords)))

        exterior_elem.appendChild(pos_elem)
        result.appendChild(pos_elem)

        return result

    def from_xml_reader(self, xml_reader):
        super().from_xml_reader(xml_reader)
        if xml_reader.name() != 'Polygon':
            return
        xml_reader.readNextStartElement()
        if xml_reader.name() != 'exterior':
            return
        xml_reader.readNextStartElement()
        if xml_reader.name() == 'LinearRing':
            xml_reader.readNextStartElement()

            if xml_reader.name() == 'posList':
                xml_reader.readNext()
                coords = xml_reader.text()
                parts = coords.split()
                for part in parts:
                    self.exterior.append(float(part))

    def to_geometry(self):
        line = QgsLineString()
        for i in range(0, len(self.exterior), 2):
            line.addVertex(QgsPoint(self.exterior[i], self.exterior[i + 1]))

        result = QgsPolygon()
        result.setExteriorRing(line)

        return result

    def from_geometry(self, geom):
        points = geom.asPolygon()[0]
        for point in points:
            self.exterior.append(point.x())
            self.exterior.append(point.y())
