
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

    if not StorageSettings.has_bucket(bucket_name):
        print('Err: NoSuchBucket')
        raise exception.NoSuchBucket()
    
    secret_access_key = StorageSettings.get_secret_access_key(
        bucket_name, access_key_id)
    if secret_access_key is None:
        print('Err: InvalidAccessKeyId')
        raise exception.InvalidAccessKeyId()

    hashed = hmac.new(secret_access_key, raw_string, hashlib.sha1).digest()
    calc_token = 'AWS {0}:{1}'.format(
        access_key_id, base64.encodestring(hashed).rstrip()
    )
    if calc_token != request.headers.get('Authorization'):
        print('Err: SignatureDoesNotMatch')
        raise exception.SignatureDoesNotMatch()


def convert_local_path(bucket_name, remote_path):
    return os.path.abspath(
        os.path.join(
            StorageSettings.settings['buckets'][bucket_name]['root_path'],
            remote_path
        )
    )


def detect_x_amz():
    ret = ''
    for key in sorted(
            filter(
                lambda x: x[0].startswith('X-Amz-'), request.headers.items()
            )
    ):
        k = key[0].lower()
        v = request.headers.get(key[0])
        ret += '{}:{}\n'.format(k, v)
    return ret


@app.route("/", methods=['HEAD'])
def head_root():
    """Check Bucket Accessing Permission."""
    # Process Header
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information('')
    access_key_id = get_request_access_key_id()

    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))

    if request_type == RequestType.VirtualHost:
        authorization_request(
            bucket_name,
            access_key_id,
            'HEAD\n\n\n{0}\n/{1}/'.format(
                request.headers.get('Date'),
                bucket_name
            )
        )
        return ('', 200)

    raise exception.NotImplemented()


@app.route("/<path:path_string>", methods=['HEAD'])
def head_object(path_string):
    """Check Object Accessing Permission."""
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()

    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))
    print('path_string:[{}]'.format(path_string))

    if request_type == RequestType.VirtualHost:
        authorization_request(
            bucket_name,
            access_key_id,
            'HEAD\n\n\n{0}\n/{1}/{2}'.format(
                request.headers.get('Date'),
                bucket_name,
                path_string
            )
        )
        local_path = convert_local_path(bucket_name, remote_path)
        print('local_path:[{}]'.format(local_path))
        if os.path.exists(local_path):
            return ('', 200)
        else:
            return ('', 404)

    raise exception.NotImplemented()

def listing_object(bucket_name):

    # Get Query Parameter
    delimiter_string = request.args.get('delimiter')
    marker_string = request.args.get('marker')
    max_keys_string = request.args.get('max-keys', '1000')
    prefix_string = request.args.get('prefix', '')
    print('delimiter:[{}]'.format(delimiter_string))
    print('marker:[{}]'.format(marker_string))
    print('max-keys:[{}]'.format(max_keys_string))
    print('prefix:[{}]'.format(prefix_string))

    # Detect Bucket objects
    objects = list()
    bucket_root = convert_local_path(bucket_name, '')
    for root, dirs, files in os.walk(
            os.path.join(
                StorageSettings.settings['buckets'][bucket_name]['root_path'],
                prefix_string
            )
    ):
        for file in files:
            abs_path = os.path.abspath(os.path.join(root, file))
            abs_path = abs_path[len('{}/'.format(bucket_root)):]
            objects.append(abs_path)

    # Generate XML (Header part)
    top = ElementTree.Element(
        'ListBucketResult',
        {'xmlns': 'http://s3.amazonaws.com/doc/2006-03-01/'})
    ElementTree.SubElement(top, 'Name').text = bucket_name
    ElementTree.SubElement(top, 'Prefix').text = prefix_string
    if delimiter_string:
        ElementTree.SubElement(top, 'Delimiter').text = delimiter_string
    else:
        ElementTree.SubElement(top, 'Delimiter')
    # ElementTree.SubElement(top, 'Marker')
    # ElementTree.SubElement(top, 'NextMarker')
    ElementTree.SubElement(top, 'KeyCount').text = str(len(objects))
    ElementTree.SubElement(top, 'MaxKeys').text = max_keys_string
    ElementTree.SubElement(top, 'IsTruncated').text = 'false'

    # Generate XML (Objects part)
    for object in objects:

        origin_object = object
        object = convert_local_path(bucket_name, object)

        with open(object, 'rb') as f:
                checksum = hashlib.md5(f.read()).hexdigest()
        #print('object:[{}]'.format(object))
        #print('exists:[{}]'.format(os.path.exists(object)))
        # Get Parameters of file
        last_modified = datetime.datetime.fromtimestamp(
            os.stat(object).st_mtime
        ).isoformat()
        etag = '&quot;{}&quot;'.format(checksum)
        size = '{}'.format(os.path.getsize(object))
        contents = ElementTree.SubElement(top, 'Contents')
        ElementTree.SubElement(contents, 'Key').text = origin_object
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

def return_object(local_path, content_type='application/octet-stream'):

    if not os.path.exists(local_path):
        raise exception.NoSuchKey()

    if not os.path.isfile(local_path):
        raise exception.InvalidArgument()

    data = ''
    with open(local_path, 'rb') as f:
        data = f.read()
        f.close()
    return Response(response=data, content_type=content_type)


@app.route("/", methods=['GET'])
def get_root():
    """Listing Object ."""
    # Process Header
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information('')
    access_key_id = get_request_access_key_id()

    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))

    if request_type != RequestType.VirtualHost:
        raise exception.NotImplemented()

    authorization_request(
        bucket_name,
        access_key_id,
        'GET\n\n\n{}\n/{}/'.format(
            request.headers.get('Date'),
            bucket_name
        )
    )
    return listing_object(bucket_name)


@app.route("/<path:path_string>", methods=['GET'])
def get_object(path_string):
    """Download Object ."""
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()

    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))
    print('path_string:[{}]'.format(path_string))

    authorization_request(
        bucket_name,
        access_key_id,
        'GET\n\n\n{}\n{}/{}/{}'.format(
            request.headers.get('Date'),
            detect_x_amz(),
            bucket_name,
            remote_path,
        )
    )

    if remote_path == '':
        return listing_object(bucket_name)

    local_path = convert_local_path(bucket_name, remote_path)
    print('local_path:[{}]'.format(local_path))
    return return_object(local_path)


def fileupload(bucket_name, remote_path):

    local_path = convert_local_path(bucket_name, remote_path)
    dir_path = os.path.dirname(local_path)

    # Create Directories
    try:
        os.makedirs(dir_path)
    except OSError:
        pass

    # Write posted data to file
    with open(local_path, 'wb') as f:
        f.write(request.data)
        f.close()

    # Check MD5
    with open(local_path, 'rb') as f:
        checksum = hashlib.md5(f.read()).hexdigest()

    # Response
    headers = {
        'ETag': '"{}"'.format(checksum)
    }

    return Response('OK', headers=headers)


@app.route("/<path:path_string>", methods=['PUT'])
def put_object(path_string):
    """Create Object."""
    validation_request_header(
        ['Host', 'Date', 'Content-Length', 'Content-Type', 'Authorization']
    )
    validation_request_authorization()
    validation_date()
    validation_filesize(request.headers.get('Content-Length'))

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()

    print('bucket_name:[{}]'.format(bucket_name))
    print('remote_path:[{}]'.format(remote_path))
    print('request_type:[{}]'.format(request_type))
    print('path_string:[{}]'.format(path_string))

    if request_type == RequestType.VirtualHost:
        authorization_request(
            bucket_name,
            access_key_id,
            'PUT\n{0}\n{1}\n{2}\n/{3}/{4}'.format(
                request.headers.get('Content-Md5'),
                request.headers.get('Content-Type'),
                request.headers.get('Date'),
                bucket_name,
                remote_path
            )
        )
        return fileupload(bucket_name, remote_path)

    raise exception.NotImplemented()


@app.route("/<path:path_string>", methods=['DELETE'])
def delete_object(path_string):
    validation_request_header(['Host', 'Date', 'Authorization'])
    validation_request_authorization()
    validation_date()

    bucket_name, remote_path, request_type = get_request_information(path_string)
    access_key_id = get_request_access_key_id()

    if request_type == RequestType.VirtualHost:
        authorization_request(
            bucket_name,
            access_key_id,
            'DELETE\n\n\n{0}\n/{1}/{2}'.format(
                request.headers.get('Date'),
                bucket_name,
                path_string
            )
        )
        local_path = convert_local_path(bucket_name, remote_path)
        if not os.path.exists(local_path):
            raise exception.NoSuchKey()
        #shutil.rmtree(local_path)
        return ('', 204)

    raise exception.NotImplemented()


if __name__ == "__main__":
    StorageSettings.load('settings.yaml')
    print StorageSettings.settings
    app.run(
        host=StorageSettings.settings['app']['host'],
        port=StorageSettings.settings['app']['port']
    )

