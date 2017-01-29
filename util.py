import os
import random
from xml.etree import ElementTree
from xml.dom import minidom

import datetime
import hashlib
from flask import (
  request
)


def xml_prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8")


def get_absolute_object_path(remote_path):
    """Generate local filepath."""
    return os.path.abspath(os.path.join('./datas', remote_path))


def get_object_list_recursive(root_path, prefix_root):
    objects = []
    for root, dirs, files in os.walk(prefix_root):
        for file in files:
            abspath = os.path.abspath(os.path.join(root, file))
            relpath = abspath[len('{}/'.format(root_path)):]
            objects.append(relpath)
    return objects, []


def get_object_list(root_path, prefix_root):
    objects = []
    prefixes = []
    for obj in os.listdir(prefix_root):
        abspath = os.path.join(prefix_root, obj)
        relpath = abspath[len('{}/'.format(root_path)):]
        if os.path.isdir(abspath):
            prefixes.append('{}/'.format(relpath))
        else:
            objects.append(relpath)
    return objects, prefixes


def generate_xml_object_list(objects, prefixes):
    delimiter_string = request.args.get('delimiter', '')
    #marker_string = request.args.get('marker', '')
    max_keys_string = request.args.get('max-keys', '1000')
    prefix_string = request.args.get('prefix', '')
    top = ElementTree.Element(
        'ListBucketResult',
        {'xmlns': 'http://s3.amazonaws.com/doc/2006-03-01/'})
    ElementTree.SubElement(top, 'Name').text = 'Bucket'
    ElementTree.SubElement(top, 'Prefix').text = prefix_string
    ElementTree.SubElement(top, 'Delimiter').text = delimiter_string
    # ElementTree.SubElement(top, 'Marker')
    # ElementTree.SubElement(top, 'NextMarker')
    ElementTree.SubElement(top, 'KeyCount').text = str(len(objects))
    ElementTree.SubElement(top, 'MaxKeys').text = max_keys_string
    ElementTree.SubElement(top, 'IsTruncated').text = 'false'
    for obj in objects:
        absolute_obj_path = get_absolute_object_path(obj)
        with open(absolute_obj_path, 'rb') as f:
                checksum = hashlib.md5(f.read()).hexdigest()
        last_modified = datetime.datetime.fromtimestamp(
            os.stat(absolute_obj_path).st_mtime
        ).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        etag = '&quot;{}&quot;'.format(checksum)
        size = '{}'.format(os.path.getsize(absolute_obj_path))
        contents = ElementTree.SubElement(top, 'Contents')
        ElementTree.SubElement(contents, 'Key').text = '{}'.format(obj)
        ElementTree.SubElement(contents, 'LastModified').text = last_modified
        ElementTree.SubElement(contents, 'ETag').text = etag
        ElementTree.SubElement(contents, 'Size').text = size
        ElementTree.SubElement(contents, 'StorageClass').text = 'Standard'
        # owner = ElementTree.SubElement(contents, 'Owner')
        # ElementTree.SubElement(owner, 'ID').text = '0001'
        # ElementTree.SubElement(owner, 'DisplayName').text = 'DefaultUser'
    cp = ElementTree.SubElement(top, 'CommonPrefixes')
    for prefix in prefixes:
        ElementTree.SubElement(cp, 'Prefix').text = prefix
    return xml_prettify(top)
