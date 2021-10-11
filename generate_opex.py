import os
import xml.etree.ElementTree as ET

from os.path import join, splitext, basename

opex = "http://www.openpreservationexchange.org/opex/v1.0"
ET.register_namespace("opex", opex)

def ignore(file):
	name, ext = splitext(file)
	return ext in ['.md5', '.opex']

def get_content(root, file):
	with open(join(root, file)) as f: s = f.read()
	return s

def output_dir(root, dirs, files):
	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	transfer = ET.SubElement(root_elem, f"{{{opex}}}Transfer")

	base = basename(root)

	source_id = ET.SubElement(transfer, f"{{{opex}}}SourceID")

	source_id.text = base

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

	# This item is 'open'
	properties = ET.SubElement(root_elem, f"{{{opex}}}Properties")
	sd = ET.SubElement(properties, f"{{{opex}}}SecurityDescriptor")
	sd.text = "open"

	root_tree = ET.ElementTree(element = root_elem)
	ET.indent(root_tree)
	root_tree.write(root + "/" + base + ".opex")


def output_file(root, file, files):
	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	filename = join(root, file)
	name, ext = splitext(file)
	md5file = name + '.md5'
	#print(f"\t-- {file}.opex --")
	if md5file in files:
		md5 = get_content(root, md5file)
		transfer = ET.SubElement(root_elem, f"{{{opex}}}Transfer")
		fixities = ET.SubElement(transfer, f"{{{opex}}}Fixities")
		ET.SubElement(fixities, f"{{{opex}}}Fixity", type="MD5", value=md5)
	else:
		print(f"\t\tWarning: no md5 for {filename}")

	root_tree = ET.ElementTree(element = root_elem)
	ET.indent(root_tree)
	root_tree.write(filename + ".opex")

for root, dirs, files in os.walk('test-pax'):

	output_dir(root, dirs, files)

	id = basename(root)

	for file in files:
		if ignore(file):
			continue
		else:
			output_file(root, file, files)

print("Finished")