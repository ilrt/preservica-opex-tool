import os
import xml.etree.ElementTree as ET
import os.path as path
import re
from pathlib import Path
import uuid

opex = "http://www.openpreservationexchange.org/opex/v1.0"
ET.register_namespace("opex", opex)
legacy = "http://preservica.com/LegacyXIP"
ET.register_namespace("legacyxip", legacy)
xip = "http://preservica.com/XIP/v6.3"
ET.register_namespace("xip", xip)

def ignore(file):
	name, ext = path.splitext(file)
	return ext in ['.md5', '.opex', '.xip']


def get_content(file):
	with open(file) as f: s = f.read()
	return s


# We expect the source dir to be already flattened
# with each item in the root dir with the calm id
def get_source_id(dir):
	path = Path(dir).parts
	if len(path) < 2:
		return None
	else:
		# CALM ids use forward slash, not dash
		return re.sub('-', '/', path[1])


def remove_top(file_path):
	path_parts = Path(file_path).parts
	return path.join(*path_parts[1:])


def is_multi_rep(root, dir):
	return path.exists(Path(root, dir, 'Representation_Preservation'))


def output_properties(root_elem, source_id):
	# This item is 'open'
	properties = ET.SubElement(root_elem, f"{{{opex}}}Properties")
	sd = ET.SubElement(properties, f"{{{opex}}}SecurityDescriptor")
	sd.text = "open"

	# CALM id again
	if source_id:
		identifiers = ET.SubElement(properties, f"{{{opex}}}Identifiers")
		identifier = ET.SubElement(identifiers, f"{{{opex}}}Identifier", type='code')
		identifier.text = source_id

	dm = ET.SubElement(root_elem, f"{{{opex}}}DescriptiveMetadata")
	lx = ET.SubElement(dm, f"{{{legacy}}}LegacyXIP")
	ar = ET.SubElement(lx, f"{{{legacy}}}AccessionRef")
	ar.text = "catalogue"


def output_dir(root, dirs, files):
	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	transfer = ET.SubElement(root_elem, f"{{{opex}}}Transfer")

	base = path.basename(root)

	source_id = get_source_id(root)

	if source_id:
		source_id_elem = ET.SubElement(transfer, f"{{{opex}}}SourceID")
		source_id_elem.text = source_id

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
		if is_multi_rep(root, dir):
			# This will be zipped up
			content = ET.SubElement(files_elem, f"{{{opex}}}File", type="content")
			content.text = dir + '.pax.zip'
			create_xip(path.join(root, dir), dir)
		else:
			folder = ET.SubElement(folders_elem, f"{{{opex}}}Folder")
			folder.text = dir

	output_properties(root_elem, source_id)

	root_tree = ET.ElementTree(element = root_elem)
	ET.indent(root_tree)
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
		return None


def output_file(root, file, files):
	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	filename = path.join(root, file)
	md5 = get_md5(filename)
	if md5:
		transfer = ET.SubElement(root_elem, f"{{{opex}}}Transfer")
		fixities = ET.SubElement(transfer, f"{{{opex}}}Fixities")
		ET.SubElement(fixities, f"{{{opex}}}Fixity", type="MD5", value=md5)
	else:
		print(f"\t\tWarning: no md5 for {filename}")

	source_id = get_source_id(root)
	output_properties(root_elem, source_id)

	root_tree = ET.ElementTree(element = root_elem)
	ET.indent(root_tree)
	root_tree.write(filename + ".opex")


def elem(ns, tag):
	return ET.Element(f"{{{ns}}}{tag}")


def subelem(parent, ns, tag, text = None):
	elem = ET.SubElement(parent, f"{{{ns}}}{tag}")

	if text:
		elem.text = text

	return elem


def create_representation(root_elem, name, parent_id, item_id, is_pres):
	rep = subelem(root_elem, xip, 'Representation')
	subelem(rep, xip, 'Ref', parent_id)
	subelem(rep, xip, 'Name', name)
	if is_pres:
		subelem(rep, xip, 'Type', 'Preservation')
	else:
		subelem(rep, xip, 'Type', 'Access')
	cont_objs = subelem(rep, xip, 'ContentObjects')
	subelem(cont_objs, xip, 'ContentObject', item_id)
	subelem(rep, xip, 'RepresentationFormats')
	subelem(rep, xip, 'RepresentationProperties')


def create_content(root_elem, parent_id, content_id):
	cont_obj = subelem(root_elem, xip, 'ContentObject')

	subelem(cont_obj, xip, 'Ref', content_id)
	subelem(cont_obj, xip, 'Title', 'Title')
	subelem(cont_obj, xip, 'SecurityTag', 'open')
	subelem(cont_obj, xip, 'Parent', parent_id)


def create_generation(root_elem, folder, subfolder, content_id,
	bitstreams, is_pres):

	if is_pres:
		original = 'true'
	else:
		original = 'false'

	gen_elem = ET.SubElement(root_elem, f"{{{xip}}}Generation",
			original = original, active = 'true')

	subelem(gen_elem, xip, 'ContentObject', content_id)
	subelem(gen_elem, xip, 'EffectiveDate', '????')

	bs_elem = subelem(gen_elem, xip, 'Bitstreams')
	for f in os.listdir(path.join(folder, subfolder)):
		if ignore(f):
			continue
		file_path = path.join(folder, subfolder, f)
		subelem(bs_elem, xip, 'Bitstream', remove_top(file_path))
		bitstreams.append(file_path)


def create_bitstream(root_elem, folder, bitstream):
	print(bitstream)
	filename = path.basename(bitstream)
	dirname = remove_top(path.dirname(bitstream))
	size = path.getsize(bitstream)
	md5 = get_md5(bitstream)

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


def create_xip(folder, item_id):
	print(f"Folder is {folder}")
	"""Create a xip file to go in the pax file"""
	root_elem = elem(xip, "XIP")

	info_obj = subelem(root_elem, xip, 'InformationObject')
	
	ref_id = str(uuid.uuid4())
	subelem(info_obj, xip, 'Ref', ref_id)

	subelem(info_obj, xip, 'Title', item_id)

	subelem(info_obj, xip, 'SecurityTag', 'open')

	pres_content_id = str(uuid.uuid4())
	create_representation(root_elem, 'Representation_Preservation',
		ref_id, pres_content_id, is_pres = True)

	acc_content_id = str(uuid.uuid4())
	create_representation(root_elem, 'Representation_Access',
		ref_id, acc_content_id, is_pres = False)

	create_content(root_elem, ref_id, pres_content_id)
	create_content(root_elem, ref_id, acc_content_id)

	bitstreams = []

	create_generation(root_elem, folder, 'Representation_Preservation', 
		pres_content_id, bitstreams, is_pres = True)

	create_generation(root_elem, folder, 'Representation_Access', 
		acc_content_id, bitstreams, is_pres = False)

	for bitstream in bitstreams:
		create_bitstream(root_elem, folder, bitstream)

	root_tree = ET.ElementTree(element = root_elem)

	ET.indent(root_tree)

	root_tree.write(path.join(folder, item_id + '.xip'))


for root, dirs, files in os.walk('FB-flattened'):

	output_dir(root, dirs, files)

	id = path.basename(root)

	for file in files:
		if ignore(file):
			continue
		else:
			output_file(root, file, files)

print("Finished")