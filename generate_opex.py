import os
import xml.etree.ElementTree as ET
import os.path as path
import re
from pathlib import Path

opex = "http://www.openpreservationexchange.org/opex/v1.0"
ET.register_namespace("opex", opex)
legacy = "http://preservica.com/LegacyXIP"
ET.register_namespace("legacyxip", legacy)

def ignore(file):
	name, ext = path.splitext(file)
	return ext in ['.md5', '.opex']


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


for root, dirs, files in os.walk('FB-flattened'):

	output_dir(root, dirs, files)

	id = path.basename(root)

	for file in files:
		if ignore(file):
			continue
		else:
			output_file(root, file, files)

print("Finished")