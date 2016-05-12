
import re
import os
import sys
import shutil

# XML
from xml.etree import ElementTree
from xml.dom import minidom

# Dateutil
import pytz
import dateutil.parser
import datetime

# SHA1-HMAC
import sha
import hmac
import base64
import hashlib

# WebApp
from flask import Flask
from flask import jsonify
from flask import request
from flask import Response

# Include
import exception

app = Flask(__name__)
app.debug = True


def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ElementTree.tostring(elem, 'utf-8')
    return rough_string
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8")


def fild_all_files(directory):
    for root, dirs, files in os.walk(directory):
        yield root
        for file in files:
            yield file


class RequestType():
    VirtualHost = 1
    Path = 2


class ObjectStorageSettings():
    root_dir = None
    access_key_id = 'record-test'
    secret_access_key = '3/Pp43hw9TQ3nKV21MiKcwrd5BofA3UjnDfihIWk'
    virtual_hostname = 'b.uhouho.net'


@app.errorhandler(exception.AppException)
def handle_invalid_usage(error):
    response = jsonify(status_code=error.status_code, message=error.message)
    response.status_code = error.status_code
    return response


def get_request_information(path_string):
    # Remove URL Query
    if path_string.count('?') > 0:
        path_string = path_string.split('?', 1)[0]
    # Virtual Host Type
    bucket_name = re.match(
        '(.*).{0}'.format(ObjectStorageSettings.virtual_hostname),
        request.headers.get('Host'))
    if bucket_name:
        bucket_name = bucket_name.group(1)
        remote_path = path_string
        return bucket_name, remote_path, RequestType.VirtualHost
    # Path Type
    if path_string.count('/') == 0:
        bucket_name = path_string
        remote_path = ''
    else:
        splited_path_string = path_string.split('/', 1)
        bucket_name = splited_path_string[0]
        remote_path = splited_path_string[1]
    return bucket_name, remote_path, RequestType.Path


def validation_request_header(keys):
    for key in keys:
        if key not in request.headers:
            raise exception.InvalidArgument()


def validation_date():
    try:
        date = dateutil.parser.parse(request.headers.get('Date'))
    except exceptions.TypeError:
        raise exception.InvalidArgument()
    tz_tokyo = pytz.timezone('Asia/Tokyo')
    diff = datetime.datetime.now(tz_tokyo) - date
    if diff > datetime.timedelta(minutes=3):
        raise exception.InvalidArgument()

def validation_filesize(size):
    if len(request.data) != int(size):
        raise exception.InvalidArgument()


def authorization(raw_string):
    """
    hashed = hmac.new(
        ObjectStorageSettings.secret_access_key,
        raw_string,hashlib.sha1
    ).digest()
    calc_token = 'AWS {0}:{1}'.format(
        ObjectStorageSettings.access_key_id,
        base64.encodestring(hashed).rstrip()
    )
    if calc_token != request.headers.get('Authorization'):
        print('**Error:SignatureDoesNotMatch**')
        raise exception.SignatureDoesNotMatch()
    """

def convert_local_path(remote_path):
    if ObjectStorageSettings.root_dir:
        return os.path.join(ObjectStorageSettings.root_dir, remote_path)
    return os.path.abspath(remote_path)


def check_object_exists(remote_path):
    local_path = convert_local_path(remote_path)
    if not os.path.exists(local_path):
        print('**Error:NoSuchKey**')
        raise exception.NoSuchKey()


@app.route("/", methods=['HEAD'])
def head_root():
    # Process Header
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_date()
    authorization(
        'HEAD\n\n\n{0}\n/'.format(request.headers.get('Date'))
    )
    bucket_name, remote_path, request_type = get_request_information('')
    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))
    # Process
    if bucket_name == 'record-test':
        return ('', 200)
    else:
        return ('', 403)

@app.route("/<path:path_string>", methods=['HEAD'])
def head_object(path_string):
    print request.headers
    # Process Header
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_date()
    authorization(
        'HEAD\n\n\n{0}\n/{1}'.format(request.headers.get('Date'), path_string)
    )
    bucket_name, remote_path, request_type = get_request_information(path_string)
    local_path = convert_local_path(remote_path)
    print('path_string:[{}]'.format(path_string))
    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('local_path:[{}]'.format(local_path))
    print('request_type:[{}]'.format(request_type))

    if os.path.exists(local_path):
        return ('', 200)
    else:
        return ('', 404)


@app.route("/", methods=['GET'])
def object_get_root():
    """Listing Object ."""
    # Process Header
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_date()
    authorization(
        'GET\n\n\n{0}\n/'.format(request.headers.get('Date'))
    )
    bucket_name, remote_path, request_type = get_request_information('')
    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))
    # Process Query
    delimiter_string = request.args.get('delimiter')
    marker_string = request.args.get('marker')
    max_keys_string = request.args.get('max-keys', '1000')
    prefix_string = request.args.get('prefix', '')
    print('delimiter:[{}]'.format(delimiter_string))
    print('marker:[{}]'.format(marker_string))
    print('max-keys:[{}]'.format(max_keys_string))
    print('prefix:[{}]'.format(prefix_string))
    # Listing
    objects = list()
    for root, dirs, files in os.walk('./{}'.format(prefix_string)):
        for file in files:
            tmp = os.path.join(root, file)
            tmp = tmp[len('./'):]
            objects.append(tmp)
    top = ElementTree.Element(
        'ListBucketResult',
        {'xmlns': 'http://s3.amazonaws.com/doc/2006-03-01/'})
    ElementTree.SubElement(top, 'Name').text = bucket_name
    ElementTree.SubElement(top, 'Prefix').text = prefix_string
    # ElementTree.SubElement(top, 'Marker')
    # ElementTree.SubElement(top, 'NextMarker')
    ElementTree.SubElement(top, 'KeyCount').text = str(len(objects))
    ElementTree.SubElement(top, 'MaxKeys').text = max_keys_string
    ElementTree.SubElement(top, 'IsTruncated').text = 'false'
    for object in objects:
        with open(object, 'rb') as f:
                checksum = hashlib.md5(f.read()).hexdigest()
        print('object:[{}]'.format(object))
        print('exists:[{}]'.format(os.path.exists(object)))
        # Get Parameters of file
        last_modified = datetime.datetime.fromtimestamp(os.stat(object).st_mtime).isoformat()
        etag = '&quot;{}&quot;'.format(checksum)
        size = '{}'.format(os.path.getsize(object))
        contents = ElementTree.SubElement(top, 'Contents')
        ElementTree.SubElement(contents, 'Key').text = object
        ElementTree.SubElement(contents, 'LastModified').text = last_modified
        ElementTree.SubElement(contents, 'ETag').text = etag
        ElementTree.SubElement(contents, 'Size').text = size
        ElementTree.SubElement(contents, 'StorageClass').text = 'Standard'
        #owner = ElementTree.SubElement(contents, 'Owner')
        #ElementTree.SubElement(owner, 'ID').text = '0001'
        #ElementTree.SubElement(owner, 'DisplayName').text = 'DefaultUser'
    # Response
    xml_data = prettify(top)
    return Response(xml_data, mimetype='application/xml')

@app.route("/<path:path_string>", methods=['GET'])
def object_get(path_string):
    """Download Object ."""
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_date()
    authorization(
        'GET\n\n\n{0}\n/{1}'.format(
            request.headers.get('Date'),
            path_string)
    )
    bucket_name, remote_path, request_type = get_request_information(
        path_string
    )
    local_path = convert_local_path(remote_path)
    print('path_string:[{}]'.format(path_string))
    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('local_path:[{}]'.format(local_path))
    print('request_type:[{}]'.format(request_type))

    if os.path.isfile(local_path):
        data = ''
        with open(local_path, 'rb') as f:
            data = f.read()
            f.close()
        return Response(response=data, content_type='application/octet-stream')

    if os.path.isdir(local_path):
        print('->Dame')
        raise exception.InvalidArgument()

    return 'NG'


@app.route("/<path:path_string>", methods=['PUT'])
def object_put(path_string):
    """Create Object."""
    validation_request_header(
        ['Host', 'Date', 'Content-Length', 'Content-Type', 'Authorization']
    )
    validation_date()
    authorization(
        'PUT\n\n{0}\n{1}\n/{2}'.format(
            request.headers.get('Content-Type'),
            request.headers.get('Date'),
            path_string)
    )
    validation_filesize(request.headers.get('Content-Length'))

    # Create Directories
    dir_path = os.path.join('./', os.path.dirname(path_string))
    try:
        os.makedirs(dir_path)
    except OSError:
        pass
    # Write posted data to file
    with open(path_string, 'wb') as f:
        f.write(request.data)
        f.close()
    # Check MD5
    with open(path_string, 'rb') as f:
        checksum = hashlib.md5(f.read()).hexdigest()
    # Response
    headers = {
        'ETag': '"{}"'.format(checksum)
    }
    return Response('OK', headers=headers)


@app.route("/<path:path_string>", methods=['DELETE'])
def object_delete(path_string):
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_date()
    authorization(
        'DELETE\n\n\n{0}\n/{1}'.format(
            request.headers.get('Date'),
            path_string)
    )
    bucket_name, remote_path, request_type = get_request_information(path_string)
    local_path = convert_local_path(remote_path)
    print 'local_path:{}'.format(local_path)
    #shutil.rmtree(local_path)
    return ('', 204)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
