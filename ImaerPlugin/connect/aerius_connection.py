import os
import json
from zipfile import ZipFile

from qgis.PyQt.QtCore import (
    QFile,
    QFileInfo,
    QIODevice,
    QVariant,
    QUrl,
    QEventLoop
)
from qgis.PyQt.QtNetwork import (
    QHttpMultiPart,
    QHttpPart,
    QNetworkRequest,
    QNetworkReply,
)

from qgis.core import (
    Qgis,
    QgsNetworkAccessManager,
    QgsBlockingNetworkRequest,
)

from qgis import processing


class AeriusConnection():

    def __init__(self, plugin, base_url=None, version=None, api_key=None, do_check_connection=True):
        self.plugin = plugin
        self.available_versions = ['7']
        self.default_base_url = 'https://connect.aerius.nl/api'
        self.default_version = '7'

        self.base_url = base_url
        self.version = version
        self.api_key = api_key

        self.connection_info = 'Not yet checked'
        self.config_is_ok = False
        self.server_is_ok = False
        self.api_key_is_ok = False

        if do_check_connection:
            self.check_connection()

    def __str__(self):
        return 'AeriusConnection[{}, {}, {}, {} {}, {}, {}]'.format(
            self.base_url,
            self.version,
            self.api_key,
            self.config_is_ok,
            self.server_is_ok,
            self.api_key_is_ok,
            self.connection_info,
        )

    def check_connection(self, test_api_key=True):
        '''
        Returns True if connection to server can be made, otherwise False. Sets
        a message to the connection_info variable.
        '''
        self.connection_info = 'OK'
        self.config_is_ok = False
        self.server_is_ok = False
        self.api_key_is_ok = False

        if self.base_url is None:
            self.connection_info = 'No base url'
            return
        if self.api_key is None or len(self.api_key) != 32:
            self.connection_info = 'No valid api key'
            return
        self.config_is_ok = True

        if self.server_is_up():
            self.server_is_ok = True
        else:
            self.connection_info = 'Server is not available'
            return

        if test_api_key:
            # Request jobs to test access with api key:
            if self.get_jobs() is None:
                self.connection_info = 'Server does not accept the api key'
                return
            else:
                self.api_key_is_ok = True
        return

    def run_request(self, api_function, method, data=None, text_parts=[], file_parts=[], with_api_key=True, blocking=True, with_version=True):
        self.plugin.log(f'run_request: {method} {api_function}', user='dev')

        manager = QgsNetworkAccessManager.instance()

        if with_version:
            url = f'{self.base_url}/v{self.version}/{api_function}'
        else:
            url = f'{self.base_url}/{api_function}'
        # url = 'http://localhost:5000' # echo server for debugging
        # print(url)
        url = QUrl(url)

        request = QNetworkRequest(url)
        # print(request)

        if with_api_key:
            # print(f'adding_api_key {self.api_key}')
            request.setRawHeader(b'api-key', self.api_key.encode('utf-8'))

        if method == 'POST':
            # print(data)
            # print(text_parts)
            # print(file_parts)

            if data is None:

                multi_part = QHttpMultiPart(QHttpMultiPart.FormDataType)

                for tp in text_parts:
                    # print(tp)
                    header = tp['header']
                    body = json.dumps(tp['body'])
                    body = body.encode('utf-8')
                    text_part = QHttpPart()
                    text_part.setHeader(QNetworkRequest.ContentDispositionHeader, QVariant(f'form-data; name="{header}"'))
                    text_part.setBody(body)
                    multi_part.append(text_part)

                for fp in file_parts:
                    # print(fp)
                    file = QFile(fp['file_name'])
                    # print(QFileInfo(file).fileName())  # <= om de file name te achterhalen en te gebruiken in de dispostion header

                    file_part = QHttpPart()
                    file_part.setHeader(QNetworkRequest.ContentTypeHeader, QVariant(fp['file_type']))
                    # This is what the echo server shows:
                    # Content-Disposition: form-data; name="filePart"; filename="AERIUS_bijlage_eigen_rekenpunten_2020.gml"
                    name = fp['name']
                    file_part.setHeader(
                        QNetworkRequest.ContentDispositionHeader,
                        QVariant(f'form-data; name="{name}"; filename="{QFileInfo(file).fileName()}"')
                    )
                    file.open(QIODevice.ReadOnly)
                    file_part.setBodyDevice(file)
                    file.setParent(multi_part)  # we cannot delete the file now, so delete it with the multi_part
                    multi_part.append(file_part)

                reply = manager.post(request, multi_part)
                multi_part.setParent(reply)
            else:
                data = json.dumps(data)
                data = data.encode('utf-8')
                request.setRawHeader(b'Content-Type', b'application/json')
                reply = manager.post(request, data)

            if blocking:
                loop = QEventLoop()
                reply.finished.connect(loop.quit)
                loop.exec_()

            return reply

        if method == 'GET':
            request.setRawHeader(b'Content-Type', b'application/json')

            qgis_request = QgsBlockingNetworkRequest()

            err = qgis_request.get(request, True)
            # print(err)

            if err > 0:
                # TODO: return error code or None or something...
                return None

            reply = qgis_request.reply()
            return reply.content()

        if method == 'DELETE':
            request.setRawHeader(b'Content-Type', b'application/json')

            # print(Qgis.QGIS_VERSION_INT)
            if Qgis.QGIS_VERSION_INT < 32000:
                # version 3.18 or lower
                reply = manager.deleteResource(request)
                if reply.error() == QNetworkReply.NoError:
                    return 1  # Just not returning None
            else:
                qgis_request = QgsBlockingNetworkRequest()
                err = qgis_request.deleteResource(request)
                # print(err)

                if err > 0:
                    # TODO: return error code or None or something...
                    return None

                reply = qgis_request.reply()
                return reply.content()

    def server_is_up(self):
        end_points = {
            '7': 'actuator/health'
        }
        end_point = end_points[self.version]
        response = self.run_request(end_point, 'GET', with_api_key=False, with_version=False)
        return response is not None

    def generate_api_key(self, email):
        self.plugin.log('generate_api_key()', user='dev')
        if self.base_url is None:
            return
        end_points = {
            '7': 'user/generateApiKey'
        }
        end_point = end_points[self.version]
        data = {'email': email}
        response = self.run_request(end_point, 'POST', data=data)
        if response is not None:
            # print(f'gelukt! {response}')
            return True
        return

    def get_jobs(self):
        self.plugin.log('get_jobs()', user='dev')
        end_points = {
            '7': 'jobs'
        }
        end_point = end_points[self.version]

        response = self.run_request(end_point, 'GET')
        if response is None:
            return

        # print(f'gelukt! {response}')
        try:
            result = json.loads(bytes(response))
            return result
        except:
            self.plugin.log('Response is not json', lvl='Warning')

    def cancel_job(self, job_key):
        self.plugin.log('cancel_job()', user='dev')
        end_points = {
            '7': f'jobs/{job_key}/cancel'
        }
        end_point = end_points[self.version]

        response = self.run_request(end_point, 'POST')
        return response

    def delete_job(self, job_key):
        self.plugin.log('delete_job()', user='dev')
        end_points = {
            '7': f'jobs/{job_key}'
        }
        end_point = end_points[self.version]

        response = self.run_request(end_point, 'DELETE')
        return response

    def download_result_zip(self, url, work_dir, base_name, unzip_gmls=True):
        '''
        Downloads a zipfile and extracts all containing gml files in the
        same directory. Returns a list of absolute gml file names.
        '''
        self.plugin.log('download_result_zip()', user='dev')
        params = {}
        params['URL'] = url
        zip_fn = os.path.join(work_dir, base_name)
        params['OUTPUT'] = zip_fn
        # print(params)

        alg_id = 'native:filedownloader'
        alg_result = processing.run(alg_id, params)
        # print(alg_result)

        result = []
        if not unzip_gmls:
            return []

        with ZipFile(zip_fn) as my_zip:
            # print(my_zip)
            for fn in my_zip.namelist():
                if fn.lower().endswith('.gml'):
                    # print(fn)
                    my_zip.extract(fn, work_dir)
                    gml_fn = os.path.join(work_dir, fn)
                    # print(gml_fn)
                    result.append(gml_fn)
        return result

    '''
    def download_zip(self, download_url):
        print('download_zip()')
        print(download_url)

        manager = QgsNetworkAccessManager.instance()

        url = QUrl(download_url)
        print(url)

        request = QNetworkRequest(url)

        manager.finished.connect(self.download_zip_handler)
        manager.get(request)


    def download_zip_handler(self, reply):
        print(reply)

        er = reply.error()
        if not er == QNetworkReply.NoError:
            print("Error occured: ", er)
            print(reply.errorString())
            return False
        with open('/home/raymond/tmp/imaer_test.zip', 'wb') as out_file:
            out_file.write(reply.content())
        return True
    '''

    def post_calculate(self, gml_files, user_options={}):
        '''Start a new calculation'''
        self.plugin.log('post_calculate()', user='dev')

        # For now this only works on 1 GML input file
        if not len(gml_files) == 1:
            return

        end_points = {
            '7': 'wnb/calculate'
        }
        end_point = end_points[self.version]

        options = {}
        options['outputType'] = 'GML'  # GML or PDF
        options['sendEmail'] = False
        # update default options with user options
        options.update(user_options)

        # print(options)

        gml_fn = gml_files[0]['gml_fn']
        situation = gml_files[0]['situation']

        base_name = QFileInfo(gml_fn).fileName()
        # print(base_name)

        text_parts = [
            {'header': 'options', 'body': options},
            {'header': 'files', 'body': [{'fileName': base_name, 'situation': situation}]}
        ]

        file_parts = []
        file_parts.append({'name': 'fileParts', 'file_name': gml_fn, 'file_type': 'application/gml+xml'})
        # file_parts.append({'name': 'fileParts', 'file_name': gml_fn, 'file_type': 'application/zip'})

        # print(file_parts)

        response = self.run_request(end_point, 'POST', text_parts=text_parts, file_parts=file_parts)
        return response

    def get_receptor_sets(self):
        'Returns a dictionary of receptor sets, or None in case of network errors'
        self.plugin.log('get_receptor_sets()', user='dev')
        end_points = {
            '7': 'receptorSets'
        }
        end_point = end_points[self.version]
        data = {}

        response = self.run_request(end_point, 'GET')

        if response is None:
            return

        self.resp = response
        result = json.loads(bytes(response))
        return result

    def post_receptor_set(self, gml_fn, name, description=''):
        '''Posts a new receptor set'''
        self.plugin.log('post_receptor_set()', user='dev')
        end_points = {
            '7': 'receptorSets'
        }
        end_point = end_points[self.version]

        text_parts = [
            {'header': 'receptorSet', 'body': {'name': name, 'description': description, 'expectRcpHeight': False}}
        ]
        file_parts = []
        file_parts.append({'name': 'filePart', 'file_name': gml_fn, 'file_type': 'application/gml+xml'})
        # print(file_parts)

        # response = self.run_request(end_point, 'POST')
        response = self.run_request(end_point, 'POST', text_parts=text_parts, file_parts=file_parts)
        # print(response)
        resp = response

        self.last_response = response
        return response

    def delete_receptor_set(self, name):
        self.plugin.log('delete_receptor_set()', user='dev')
        api_function = f'receptorSets/{name}'

        response = self.run_request(api_function, 'DELETE')

        return response

    def post_validate(self, gml_fn):
        self.plugin.log('post_validate()', user='dev')
        end_points = {
            '7': 'utility/validate'
        }
        end_point = end_points[self.version]

        file_parts = []
        file_parts.append({'name': 'filePart', 'file_name': gml_fn, 'file_type': 'application/gml+xml'})
        # print(file_parts)

        response = self.run_request(end_point, 'POST', file_parts=file_parts)
        # print(response)

        return response
