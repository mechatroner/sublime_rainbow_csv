#!/usr/bin/env python

import sys
import os
import argparse
import random
import xml.etree.ElementTree as ET
import copy
import xml.dom.minidom


def remove_blanks_from_xml(xml_str):
    lines = xml_str.split('\n')
    lines = [l.strip() for l in lines]
    lines = [l for l in lines if len(l)]
    return ''.join(lines)

def parse_xml_str(xml_str):
    xml_str = remove_blanks_from_xml(xml_str)
    return ET.fromstring(xml_str)

def pretty_print(root):
    xml_str = ET.tostring(root)
    return xml.dom.minidom.parseString(xml_str).toprettyxml()


def add_plist_entry(root, key, value):
    cur = ET.Element('key')
    cur.text = key
    root.append(cur)
    cur = ET.Element('string')
    cur.text = value
    root.append(cur)


def make_color_entry(scope, color, font = None):
    result = ET.Element('dict')
    add_plist_entry(result, 'name', 'rainbow csv ' + scope)
    add_plist_entry(result, 'scope', scope)

    cur = ET.Element('key')
    cur.text = 'settings'
    result.append(cur)
    settings = ET.Element('dict')

    if font != None:
        add_plist_entry(settings, 'fontStyle', font)
    add_plist_entry(settings, 'foreground', color)
    result.append(settings)
    return result


def convert_colorscheme(root):
    root = copy.deepcopy(root)
    array_elem = root.findall('./dict/array')
    if len(array_elem) != 1:
        return None
    array_elem = array_elem[0]
    array_elem.append(make_color_entry('rainbow1', '#FF0000', 'bold'))
    return root



def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument('--verbose', action='store_true', help='Run in verbose mode')
    #parser.add_argument('--num_iter', type=int, help='number of iterations option')
    parser.add_argument('src_path', help='example of positional argument')
    args = parser.parse_args()

    #num_iter = args.num_iter
    src_path = args.src_path
    root = parse_xml_str(open(src_path).read())
    converted = convert_colorscheme(root)
    #print converted
    #print ET.tostring(converted)
    print pretty_print(converted)

    #for line in sys.stdin:
    #    line = line.rstrip('\n')
    #    fields = line.split('\t')

if __name__ == '__main__':
    main()
