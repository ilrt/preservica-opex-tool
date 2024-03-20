import os
import xml.etree.ElementTree as ET
import os.path as path
import re
from pathlib import Path
import uuid
import sys
import datetime
import hashlib

opex = "http://www.openpreservationexchange.org/opex/v1.0"
ET.register_namespace("opex", opex)


def output_properties(root_elem, name, not_virtual):
    # This item is 'open'
    properties = subelem(root_elem, opex, 'Properties')
    sd = subelem(properties, opex, 'SecurityDescriptor')
    sd.text = "open"

    # if level in [1,2]:

    ids = subelem(properties, opex, 'Identifiers')
    id_elem = subelem(ids, opex, 'Identifier', text=name,  # Calm id?
                      type='code')

    dm = subelem(root_elem, opex, 'DescriptiveMetadata')
    lx = subelem(dm, 'legacy', 'LegacyXIP')
    if not_virtual:
        subelem(lx, 'legacy', 'AccessionRef', 'catalogue')
    else:
        subelem(lx, 'legacy', 'Virtual', 'true')


def output_dir(name, dirs, files):

    root_elem = elem(opex, 'OPEXMetadata')
    transfer = subelem(root_elem, opex, 'Transfer')

    manifest_elem = ET.SubElement(transfer, f"{{{opex}}}Manifest")
    files_elem = ET.SubElement(manifest_elem, f"{{{opex}}}Files")
    for filename, fileinfo in files.items():
        if fileinfo.is_metadata:
            type = 'metadata'
        else:
            type = 'content'

        content = ET.SubElement(files_elem, f"{{{opex}}}File", type=type)
        content.text = filename

    folders_elem = ET.SubElement(manifest_elem, f"{{{opex}}}Folders")

    for dirname, dir in dirs.items():
        folder = ET.SubElement(folders_elem, f"{{{opex}}}Folder")
        folder.text = dirname

    output_properties(root_elem, name, len(dirs) == 0)

    root_tree = ET.ElementTree(element=root_elem)
    ET.indent(root_tree)

    return root_tree


def output_pax_file(root, file):

    root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
    filename = path.join(root, file)

    code = file[:-8]  # remove .pax.zip

    output_properties(root_elem, code, 2)

    root_tree = ET.ElementTree(element=root_elem)
    ET.indent(root_tree)
    root_tree.write(filename + ".opex")


def output_file(file_info):

    root_elem = elem(opex, "OPEXMetadata")
    if file_info.fixity:
        transfer = subelem(root_elem, opex, "Transfer")
        fixities = subelem(transfer, opex, "Fixities")
        subelem(fixities, opex, "Fixity", type=file_info.fixity_type,
                value=file_info.fixity)
    else:
        print(f"\t\tWarning: no fixity for {file_info.filename}")

    props = subelem(root_elem, opex, 'Properties')
    subelem(props, opex, 'SecurityDescriptor', 'open')

    root_tree = ET.ElementTree(element=root_elem)
    ET.indent(root_tree)
    return root_tree


def elem(ns, tag):
    return ET.Element(f"{{{ns}}}{tag}")


def subelem(parent, ns, tag, text=None, **kwargs):
    elem = ET.SubElement(parent, f"{{{ns}}}{tag}", **kwargs)

    if text:
        elem.text = text

    return elem
