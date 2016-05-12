
# XML
import random
from xml.etree import ElementTree
from xml.dom import minidom


def xml_prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8")


def gen_random_str(length):
    """UID Generator."""
    source_str = 'abcdefghijklmnopqrstuvwxyz0123456789'
    random.choice(source_str)
    return "".join([random.choice(source_str) for x in xrange(length)])

