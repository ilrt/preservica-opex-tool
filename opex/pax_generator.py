import xml.etree.ElementTree as ET
import zipfile
import uuid
import datetime
import os
from opex.util import elem, subelem
import logging

xip = "http://preservica.com/XIP/v6.3"
ET.register_namespace("xip", xip)

logger = logging.getLogger(__name__)


def create_representation(root_elem, name, parent_id, item_id, is_pres):
    rep = subelem(root_elem, xip, 'Representation')
    subelem(rep, xip, 'InformationObject', parent_id)
    subelem(rep, xip, 'Name', name)
    if is_pres:
        subelem(rep, xip, 'Type', 'Preservation')
    else:
        subelem(rep, xip, 'Type', 'Access')
    cont_objs = subelem(rep, xip, 'ContentObjects')
    subelem(cont_objs, xip, 'ContentObject', item_id)
    subelem(rep, xip, 'RepresentationFormats')
    subelem(rep, xip, 'RepresentationProperties')


def create_content(root_elem, parent_id, content_id, name):
    cont_obj = subelem(root_elem, xip, 'ContentObject')

    subelem(cont_obj, xip, 'Ref', content_id)
    subelem(cont_obj, xip, 'Title', name)
    subelem(cont_obj, xip, 'SecurityTag', 'open')
    subelem(cont_obj, xip, 'Parent', parent_id)


def zip_location(fileinfo):
    if fileinfo.is_access:
        return ('Representation_Access', fileinfo.filename)
    else:
        return ('Representation_Preservation', fileinfo.filename)


def create_generation(root_elem, entries, content_id, is_pres):

    if is_pres:
        original = 'true'
    else:
        original = 'false'

    gen_elem = subelem(root_elem, xip, 'Generation',
                       original=original, active='true')

    subelem(gen_elem, xip, 'ContentObject', content_id)
    subelem(gen_elem, xip, 'EffectiveDate', datetime.date.today().isoformat())

    bs_elem = subelem(gen_elem, xip, 'Bitstreams')

    for file in entries:
        subelem(bs_elem, xip, 'Bitstream', '/'.join(zip_location(file)))


def create_bitstream(root_elem, fileinfo):
    dirname, filename = zip_location(fileinfo)
    size = os.path.getsize(fileinfo.source_path)

    bs_elem = subelem(root_elem, xip, 'Bitstream')
    subelem(bs_elem, xip, 'Filename', filename)
    subelem(bs_elem, xip, 'FileSize', str(size))
    subelem(bs_elem, xip, 'PhysicalLocation', dirname)

    if fileinfo.fixity:
        fxs = subelem(bs_elem, xip, 'Fixities')
        fx = subelem(fxs, xip, 'Fixity')
        subelem(fx, xip, 'FixityAlgorithmRef', fileinfo.fixity_type)
        subelem(fx, xip, 'FixityValue', fileinfo.fixity)
    else:
        logger.warn(f"No fixity for {fileinfo.source_path}")


def create_xip(dir):
    """Create a xip file to go in the pax file"""
    root_elem = elem(xip, "XIP")

    info_obj = subelem(root_elem, xip, 'InformationObject')

    ref_id = str(uuid.uuid4())
    subelem(info_obj, xip, 'Ref', ref_id)

    subelem(info_obj, xip, 'Title', dir.dir_id)

    subelem(info_obj, xip, 'SecurityTag', 'open')

    pres_content_id = str(uuid.uuid4())
    create_representation(root_elem, 'Representation_Preservation',
                          ref_id, pres_content_id, is_pres=True)

    acc_content_id = str(uuid.uuid4())
    create_representation(root_elem, 'Representation_Access',
                          ref_id, acc_content_id, is_pres=False)

    create_content(root_elem, ref_id, pres_content_id, 'Preservation content')
    create_content(root_elem, ref_id, acc_content_id, 'Access content')

    create_generation(root_elem, dir.preservation_files(), pres_content_id,
                      is_pres=True)
    create_generation(root_elem, dir.access_files(), acc_content_id,
                      is_pres=False)

    for fileinfo in dir.asset_files():
        create_bitstream(root_elem, fileinfo)

    root_tree = ET.ElementTree(element=root_elem)

    ET.indent(root_tree)

    return root_tree


def create_pax(dir, zip_path, dry_run=False):

    if dry_run:
        logger.info(f"Dry run, not creating zip {zip_path}")

    if not dry_run:
        zip = zipfile.ZipFile(zip_path, mode='w')

    xip = create_xip(dir)

    if not dry_run:
        zip.writestr(dir.name + '.xip', ET.tostring(xip.getroot(),
                                                    encoding='utf-8'))

    to_remove = []

    for fileinfo in dir.asset_files():
        if not dry_run:
            zip.write(fileinfo.source_path, '/'.join(zip_location(fileinfo)))
        to_remove.append(fileinfo)

    # Once zipped they will be present in another form, so remove them
    for fileinfo in to_remove:
        dir.remove_file(fileinfo)

    if not dry_run:
        zip.close()
