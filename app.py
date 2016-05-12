
import re
import os
import shutil

# XML
from xml.etree import ElementTree

# YAML
import yaml

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
import util

app = Flask(__name__)
app.debug = True


class RequestType():
    VirtualHost = 1
    Path = 2


class StorageSettings():
    settings = None

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'r') as f:
            cls.settings = yaml.load(f)
            f.close()

    @classmethod
    def has_bucket(cls, bucket_name):
        return bucket_name in cls.settings['buckets']

    @classmethod
    def get_secret_access_key(cls, bucket_name, access_key_id):
        credentials = filter(
            lambda x: x['access_key_id'] == access_key_id,
            cls.settings['buckets'][bucket_name]['credentials']
        )
        if len(credentials) == 1:
            return credentials[0]['secret_access_key']
        else:
            return None
    

@app.errorhandler(exception.AppException)
def handle_invalid_usage(error):
    response = jsonify(status_code=error.status_code, message=error.message)
    response.status_code = error.status_code
    return response


def get_request_access_key_id():
    auth_string = request.headers.get('Authorization').split(' ')[1]
    return auth_string.split(':')[0]


def get_request_information(path_string):
    # Remove URL Query
    if path_string.count('?') > 0:
        path_string = path_string.split('?', 1)[0]
    # Virtual Host Type
    bucket_name = re.match(
        '(.*).{0}'.format(StorageSettings.settings['app']['virtual_host']),
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


def validation_request_authorization():
    auth_string = request.headers.get('Authorization').split(' ')
    if len(auth_string) != 2:
        raise exception.InvalidArgument()
    if auth_string[0] != 'AWS':
        raise exception.InvalidArgument()
    if auth_string[1].count(':') != 1:
        raise exception.InvalidArgument()


def validation_date():
    try:
        date = dateutil.parser.parse(request.headers.get('Date'))
    except exception.TypeError:
        raise exception.InvalidArgument()
    tz_tokyo = pytz.timezone('Asia/Tokyo')
    diff = datetime.datetime.now(tz_tokyo) - date
    if diff > datetime.timedelta(minutes=3):
        raise exception.InvalidArgument()


def validation_filesize(size):
    if len(request.data) != int(size):
        raise exception.InvalidArgument()


def authorization_request(bucket_name, access_key_id, raw_string):
    print bucket_name
    print access_key_id
    print access_key_id
    """
    if not StorageSettings.has_bucket(bucket_name):
        print('Err: NoSuchBucket')
        raise exception.NoSuchBucket()
    
    secret_access_key = StorageSettings.get_secret_access_key(bucket_name, access_key_id)
    if secret_access_key is None:
        print('Err: InvalidAccessKeyId')
        raise exception.InvalidAccessKeyId()
    """
    """
    hashed = hmac.new(
        StorageSettings.secret_access_key,
        raw_string,hashlib.sha1
    ).digest()
    calc_token = 'AWS {0}:{1}'.format(
        StorageSettings.access_key_id,
        base64.encodestring(hashed).rstrip()
    )
    if calc_token != request.headers.get('Authorization'):
        print('**Error:SignatureDoesNotMatch**')
        raise exception.SignatureDoesNotMatch()
    """


def convert_local_path(remote_path):
    return os.path.abspath(remote_path)


@app.route("/", methods=['HEAD'])
def head_root():
    """Check Bucket Accessing Permission."""
    # Process Header
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information('')
    access_key_id = get_request_access_key_id()
    authorization_request(
        bucket_name,
        access_key_id,
        'HEAD\n\n\n{0}\n/'.format(request.headers.get('Date'))
    )

    # Debug
    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))

    return ('', 200)


@app.route("/<path:path_string>", methods=['HEAD'])
def head_object(path_string):
    """Check Object Accessing Permission."""
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()
    authorization_request(
        bucket_name,
        access_key_id,
        'HEAD\n\n\n{0}\n/{1}'.format(request.headers.get('Date'), path_string)
    )

    local_path = convert_local_path(remote_path)

    # Debug
    print('path_string:[{}]'.format(path_string))
    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))
    print('local_path:[{}]'.format(local_path))

    # Object Check
    if os.path.exists(local_path):
        return ('', 200)
    else:
        return ('', 404)


@app.route("/", methods=['GET'])
def get_root():
    """Listing Object ."""
    # Process Header
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information('')
    access_key_id = get_request_access_key_id()
    authorization_request(
        bucket_name,
        access_key_id,
        'GET\n\n\n{0}\n/'.format(request.headers.get('Date'))
    )
    
    delimiter_string = request.args.get('delimiter')
    marker_string = request.args.get('marker')
    max_keys_string = request.args.get('max-keys', '1000')
    prefix_string = request.args.get('prefix', '')

    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))
    print('delimiter:[{}]'.format(delimiter_string))
    print('marker:[{}]'.format(marker_string))
    print('max-keys:[{}]'.format(max_keys_string))
    print('prefix:[{}]'.format(prefix_string))

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
        last_modified = datetime.datetime.fromtimestamp(
            os.stat(object).st_mtime
        ).isoformat()
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
    xml_data = util.xml_prettify(top)
    return Response(xml_data, mimetype='application/xml')


@app.route("/<path:path_string>", methods=['GET'])
def get_object(path_string):
    """Download Object ."""
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()
    authorization_request(
        bucket_name,
        access_key_id,
        'GET\n\n\n{0}\n/{1}'.format(request.headers.get('Date'), path_string)
    )
    
    local_path = convert_local_path(remote_path)
    print('path_string:[{}]'.format(path_string))
    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('local_path:[{}]'.format(local_path))
    print('request_type:[{}]'.format(request_type))

    if not os.path.exists(local_path):
        raise exception.NoSuchKey()

    if os.path.isfile(local_path):
        data = ''
        with open(local_path, 'rb') as f:
            data = f.read()
            f.close()
        return Response(response=data,
                        content_type='application/octet-stream')
    else:
        raise exception.InvalidArgument()


@app.route("/<path:path_string>", methods=['PUT'])
def put_object(path_string):
    """Create Object."""
    validation_request_header(
        ['Host', 'Date', 'Content-Length', 'Content-Type', 'Authorization']
    )
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()
    authorization_request(
        bucket_name,
        access_key_id,
        'PUT\n\n{0}\n{1}\n/{2}'.format(
            request.headers.get('Content-Type'),
            request.headers.get('Date'),
            path_string
        )
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
def delete_object(path_string):
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()
    authorization_request(
        bucket_name,
        access_key_id,
        'DELETE\n\n\n{0}\n/{1}'.format(request.headers.get('Date'), path_string)
    )
    bucket_name, remote_path, request_type = get_request_information(path_string)
    local_path = convert_local_path(remote_path)
    print 'local_path:{}'.format(local_path)
    #shutil.rmtree(local_path)
    return ('', 204)


if __name__ == "__main__":
    StorageSettings.load('settings.yaml')
    print StorageSettings.settings
    app.run(
        host=StorageSettings.settings['app']['host'],
        port=StorageSettings.settings['app']['port']
    )

