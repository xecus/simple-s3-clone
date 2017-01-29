
import os
import re
import shutil

import util
import exception
from flask import (
    Flask,
    request,
    g,
    jsonify,
    Response
)
import hmac
import base64
import hashlib

app = Flask(__name__)
app.debug = True

hostname = 'b.tgr.tokyo'
users = [
    ('hogehoge_user1', 'hogehoge_password1'),
    ('hogehoge_user2', 'hogehoge_password2'),
    ('hogehoge_user3', 'hogehoge_password3'),
]


def get_auth_info():
    if 'Authorization' not in request.headers:
        raise exception.InvalidArgument()
    auth_string = request.headers.get('Authorization').split(' ')
    if len(auth_string) != 2:
        raise exception.InvalidArgument()
    return auth_string[1]


def get_date_on_request():
    for key in ['Date', 'X-Amz-Date']:
        if key in request.headers:
            break
    else:
        raise exception.InvalidArgument()
    return request.headers[key]


def get_x_amz_headers():
    return filter(lambda x: x[0].startswith('X-Amz-'), request.headers.items())


def generate_x_amz_string():
    ret = ''
    for key in sorted(get_x_amz_headers()):
        k = key[0].lower()
        v = request.headers.get(key[0])
        ret += '{}:{}\n'.format(k, v)
    return ret


def auth_check(auth_info, auth_raw_string):
    if ':' not in auth_info:
        raise exception.InvalidArgument()
    access_key_id = auth_info.split(':')[0]
    user = filter(lambda x: x[0] == access_key_id, users)
    if len(user) == 0:
        raise exception.InvalidAccessKeyId()
    secret_access_key = user[0][1]
    hashed = hmac.new(secret_access_key, auth_raw_string,
                      hashlib.sha1).digest()
    generated_signature = '{}:{}'.format(
        access_key_id, base64.encodestring(hashed).rstrip())
    if auth_info != generated_signature:
        raise exception.SignatureDoesNotMatch()


def generate_auth_string():
    s = '{}\n{}\n{}\n{}\n{}{}'.format(
        request.method,
        request.headers.get('Content-Md5', ''),
        request.headers.get('Content-Type', ''),
        g.date,
        g.x_amz_string,
        request.path
    )
    return s


def get_bucket_name_and_resource_path():
    # Virtual Host Type
    r = re.match(r'(.*).{0}'.format(hostname), request.headers.get('Host'))
    if r:
        return r.group(1), request.path
    # Path Specified Type
    r = re.match(r'/(.*)/(.*)', request.path)
    if r:
        return request.path[1:].split('/', 1)
    # Error
    raise exception.NotImplemented()


@app.before_request
def before_request():

    g.auth_info = get_auth_info()
    g.date = get_date_on_request()
    g.x_amz_string = generate_x_amz_string()
    g.auth_raw_string = generate_auth_string()
    g.bucket_name, g.resource_path = get_bucket_name_and_resource_path()

    # print(request.path)
    # print(request.method)
    # print(request.headers)
    # print('g.auth_info=[{}]'.format(g.auth_info))
    # print('g.date=[{}]'.format(g.date))
    # print('g.x_amz_string=[{}]'.format(g.x_amz_string.rstrip()))
    # print('g.auth_raw_string=[{}]'.format(','.join(g.auth_raw_string.split('\n'))))
    # print('g.bucket_name=[{}]'.format(g.bucket_name))
    # print('g.resource_path=[{}]'.format(g.resource_path))

    auth_check(g.auth_info, g.auth_raw_string)


@app.errorhandler(exception.AppException)
def handle_app_error(error):
    response = jsonify(status_code=error.status_code, message=error.message)
    response.status_code = error.status_code
    return response


@app.route("/")
def get_request_without_path():
    return get_request_with_path('')


@app.route("/<path:path>")
def get_request_with_path(path):
    if g.resource_path == '':
        return process_object_list()
    else:
        return download_object()


@app.route("/<path:path>", methods=['PUT'])
def put_request_with_path(path):
    if int(request.headers.get('Content-Length')) != len(request.data):
        raise exception.MissingContentLength()
    if g.resource_path[-1] == '/':
        return create_prefix()
    else:
        return create_object()


@app.route("/<path:path>", methods=['DELETE'])
def delete_request_with_path(path):
    if g.resource_path[-1] == '/':
        return delete_prefix()
    else:
        return delete_object()


def process_object_list():
    delimiter_string = request.args.get('delimiter', '')
    #marker_string = request.args.get('marker', '')
    #max_keys_string = request.args.get('max-keys', '1000')
    prefix_string = request.args.get('prefix', '')
    # print('delimiter_string=[{}]'.format(delimiter_string))
    # print('marker_string=[{}]'.format(marker_string))
    # print('max_keys_string=[{}]'.format(max_keys_string))
    # print('prefix_string=[{}]'.format(prefix_string))
    objects = []
    common_prefixes = []
    root_path = util.get_absolute_object_path('')
    prefix_root = util.get_absolute_object_path(prefix_string)
    if delimiter_string == '':
        objects, common_prefixes = util.get_object_list_recursive(
            root_path, prefix_root)
    elif delimiter_string == '/':
        objects, common_prefixes = util.get_object_list(root_path, prefix_root)
    else:
        raise exception.NotImplemented()
    # print objects
    # print common_prefixes
    xml_data = util.generate_xml_object_list(objects, common_prefixes)
    return Response(xml_data, mimetype='application/xml')


def download_object():
    content_type = 'application/octet-stream'
    object_path = util.get_absolute_object_path(g.resource_path)
    if not os.path.exists(object_path):
        raise exception.NoSuchKey()
    if not os.path.isfile(object_path):
        raise exception.InvalidArgument()
    with open(object_path, 'rb') as f:
        data = f.read()
        f.close()
    return Response(response=data, content_type=content_type)


def create_prefix():
    dir_path = util.get_absolute_object_path(g.resource_path)
    try:
        os.makedirs(dir_path)
    except OSError:
        pass
    return Response('OK')


def create_object():
    object_path = util.get_absolute_object_path(g.resource_path)
    dir_path = os.path.dirname(object_path)
    try:
        os.makedirs(dir_path)
    except OSError:
        pass
    with open(object_path, 'wb') as f:
        f.write(request.data)
        f.close()
    with open(object_path, 'rb') as f:
        checksum = hashlib.md5(f.read()).hexdigest()
    headers = {
        'ETag': '"{}"'.format(checksum)
    }
    return Response('OK', headers=headers)


def delete_prefix():
    object_path = util.get_absolute_object_path(g.resource_path)
    if not os.path.exists(object_path):
        raise exception.NoSuchKey()
    shutil.rmtree(object_path)
    return ('', 204)


def delete_object():
    object_path = util.get_absolute_object_path(g.resource_path)
    if not os.path.exists(object_path):
        raise exception.NoSuchKey()
    os.remove(object_path)
    return ('', 204)


if __name__ == "__main__":
    app.run()
