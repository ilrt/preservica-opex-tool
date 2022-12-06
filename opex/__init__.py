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
legacy = "http://preservica.com/LegacyXIP"
ET.register_namespace("legacyxip", legacy)
xip = "http://preservica.com/XIP/v6.3"
ET.register_namespace("xip", xip)


# TAKEN FROM ET SOURCE
def indent(tree, space="  ", level=0):
    """Indent an XML document by inserting newlines and indentation space
    after elements.
    *tree* is the ElementTree or Element to modify.  The (root) element
    itself will not be changed, but the tail text of all elements in its
    subtree will be adapted.
    *space* is the whitespace to insert for each indentation level, two
    space characters by default.
    *level* is the initial indentation level. Setting this to a higher
    value than 0 can be used for indenting subtrees that are more deeply
    nested inside of a document.
    """
    if isinstance(tree, ET.ElementTree):
        tree = tree.getroot()
    if level < 0:
        raise ValueError(f"Initial indentation level must be >= 0, got {level}")
    if not len(tree):
        return

    # Reduce the memory consumption by reusing indentation strings.
    indentations = ["\n" + level * space]

    def _indent_children(elem, level):
        # Start a new indentation level for the first child.
        child_level = level + 1
        try:
            child_indentation = indentations[child_level]
        except IndexError:
            child_indentation = indentations[level] + space
            indentations.append(child_indentation)

        if not elem.text or not elem.text.strip():
            elem.text = child_indentation

        for child in elem:
            if len(child):
                _indent_children(child, child_level)
            if not child.tail or not child.tail.strip():
                child.tail = child_indentation

        # Dedent after the last child by overwriting the previous indentation.
        if not child.tail.strip():
            child.tail = indentations[level]

    _indent_children(tree, 0)


def ignore(file):
	name, ext = path.splitext(file)
	return ext in ['.md5', '.opex', '.xip']


def get_content(file):
	with open(file) as f: s = f.read()
	return s.strip()


# We expect the source dir to be already flattened
# with each item in the root dir with the calm id
def to_calm_id(basename):
	# CALM ids use forward slash, not dash
	return re.sub('-', '/', basename)
	

def output_properties(root_elem, code, level):
	# This item is 'open'
	properties = subelem(root_elem, opex, 'Properties')
	sd = subelem(properties, opex, 'SecurityDescriptor')
	sd.text = "open"

	if level in [1,2]:

		ids = subelem(properties, opex, 'Identifiers')
		id_elem = subelem(ids, opex, 'Identifier', text=to_calm_id(code), type='code')

		dm = subelem(root_elem, opex, 'DescriptiveMetadata')
		lx = subelem(dm, legacy, 'LegacyXIP')
		if level == 2:
			subelem(lx, legacy, 'AccessionRef', 'catalogue')
		else:
			subelem(lx, legacy, 'Virtual', 'true')


def output_dir(root, dirs, files, level):

	root_elem = elem(opex, 'OPEXMetadata')
	transfer = subelem(root_elem, opex, 'Transfer')

	base = path.basename(root)

	manifest_elem = ET.SubElement(transfer, f"{{{opex}}}Manifest")
	files_elem = ET.SubElement(manifest_elem, f"{{{opex}}}Files")
	for file in files:
		if ignore(file):
			continue
		content = ET.SubElement(files_elem, f"{{{opex}}}File", type="content")
		content.text = file
		metadata = ET.SubElement(files_elem, f"{{{opex}}}File", type="metadata")
		metadata.text = file + ".opex"

	folders_elem = ET.SubElement(manifest_elem, f"{{{opex}}}Folders")
	
	for dir in dirs:
		folder = ET.SubElement(folders_elem, f"{{{opex}}}Folder")
		folder.text = dir

	output_properties(root_elem, base, level)

	root_tree = ET.ElementTree(element = root_elem)
	indent(root_tree)
	root_tree.write(root + "/" + base + ".opex")


def get_md5(filename):
	name, ext = path.splitext(filename)
	md5file = name + '.md5'
	if path.exists(md5file):
		return get_content(md5file)
	elif path.islink(filename):
		link = Path(filename)
		target = link.resolve()
		return get_md5(str(target))
	else:
		# generate md5 from content
		print(f"\t\tWarning: no md5 for {filename}, generating...")
		with open(filename, "rb") as f:
			file_hash = hashlib.md5()
			chunk = f.read(8192)
			while chunk:
				file_hash.update(chunk)
				chunk = f.read(8192)
			return file_hash.hexdigest()

def output_pax_file(root, file):

	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	filename = path.join(root, file)
	
	code = file[:-8] # remove .pax.zip

	output_properties(root_elem, code, 2)

	root_tree = ET.ElementTree(element = root_elem)
	indent(root_tree)
	root_tree.write(filename + ".opex")


def output_file(root, file):

	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	filename = path.join(root, file)
	md5 = get_md5(filename)
	if md5:
		transfer = ET.SubElement(root_elem, f"{{{opex}}}Transfer")
		fixities = ET.SubElement(transfer, f"{{{opex}}}Fixities")
		ET.SubElement(fixities, f"{{{opex}}}Fixity", type="MD5", value=md5)
	else:
		print(f"\t\tWarning: no md5 for {filename}")

	props = subelem(root_elem, opex, 'Properties')
	subelem(props, opex, 'SecurityDescriptor', 'open')

	root_tree = ET.ElementTree(element = root_elem)
	indent(root_tree)
	root_tree.write(filename + ".opex")


def elem(ns, tag):
	return ET.Element(f"{{{ns}}}{tag}")


def subelem(parent, ns, tag, text = None, **kwargs):
	elem = ET.SubElement(parent, f"{{{ns}}}{tag}", **kwargs)

	if text:
		elem.text = text

	return elem


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


def to_unix(path):
	"""Take path, return a unix path (sloppy, but ok)"""
	return path.replace("\\","/")


def create_generation(root_elem, entries, content_id, is_pres):

	if is_pres:
		original = 'true'
	else:
		original = 'false'

	gen_elem = ET.SubElement(root_elem, f"{{{xip}}}Generation",
			original = original, active = 'true')

	subelem(gen_elem, xip, 'ContentObject', content_id)
	subelem(gen_elem, xip, 'EffectiveDate', datetime.date.today().isoformat())

	bs_elem = subelem(gen_elem, xip, 'Bitstreams')

	for source, zip_location, is_preserve in entries:
		# Use unix path for location
		subelem(bs_elem, xip, 'Bitstream', to_unix(zip_location))


def create_bitstream(root_elem, source, zip_location):
	filename = path.basename(zip_location)
	dirname = path.dirname(zip_location)
	size = path.getsize(source)
	md5 = get_md5(source)

	bs_elem = subelem(root_elem, xip, 'Bitstream')
	subelem(bs_elem, xip, 'Filename', filename)
	subelem(bs_elem, xip, 'FileSize', str(size))
	subelem(bs_elem, xip, 'PhysicalLocation', dirname)

	if md5:
		fxs = subelem(bs_elem, xip, 'Fixities')
		fx = subelem(fxs, xip, 'Fixity')
		subelem(fx, xip, 'FixityAlgorithmRef', 'MD5')
		subelem(fx, xip, 'FixityValue', md5)
	else:
		print(f"\t\tWarning: no md5 for {bitstream}")


def create_xip(asset_id, entries):
	"""Create a xip file to go in the pax file"""
	root_elem = elem(xip, "XIP")

	info_obj = subelem(root_elem, xip, 'InformationObject')
	
	ref_id = str(uuid.uuid4())
	subelem(info_obj, xip, 'Ref', ref_id)

	subelem(info_obj, xip, 'Title', asset_id)

	subelem(info_obj, xip, 'SecurityTag', 'open')

	pres_content_id = str(uuid.uuid4())
	create_representation(root_elem, 'Representation_Preservation',
		ref_id, pres_content_id, is_pres = True)

	acc_content_id = str(uuid.uuid4())
	create_representation(root_elem, 'Representation_Access',
		ref_id, acc_content_id, is_pres = False)

	create_content(root_elem, ref_id, pres_content_id, 'Presentation content')
	create_content(root_elem, ref_id, acc_content_id, 'Access content')

	# Group entries by preservation and access
	pres_entries = [(source, zip_location, is_preserve) for source, zip_location, is_preserve in entries if is_preserve]
	access_entries = [(source, zip_location, is_preserve) for source, zip_location, is_preserve in entries if not is_preserve]

	create_generation(root_elem, pres_entries, pres_content_id, is_pres = True)
	create_generation(root_elem, access_entries, acc_content_id, is_pres = False)

	for source, zip_location, is_preserve in entries:
		create_bitstream(root_elem, source, zip_location)

	root_tree = ET.ElementTree(element = root_elem)

	indent(root_tree)

	return root_tree
