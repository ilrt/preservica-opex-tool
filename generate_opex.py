import os
import xml.etree.ElementTree as ET
import os.path as path
import re
from pathlib import Path
import uuid
import sys

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
	return s


# We expect the source dir to be already flattened
# with each item in the root dir with the calm id
def to_calm_id(basename):
	# CALM ids use forward slash, not dash
	return re.sub('-', '/', basename)


def remove_top(file_path):
	path_parts = Path(file_path).parts
	return path.join(*path_parts[2:])


def get_level(dir):
	return len(Path(dir).parts) - 1


def in_pax(dir):
	return '/Representation' in dir


def is_multi_rep1(root):
	return path.exists(Path(root, 'Representation_Preservation'))


def is_multi_rep(root, dir):
	return path.exists(Path(root, dir, 'Representation_Preservation'))


def output_properties(root_elem, code, level):
	# This item is 'open'
	properties = ET.SubElement(root_elem, f"{{{opex}}}Properties")
	sd = ET.SubElement(properties, f"{{{opex}}}SecurityDescriptor")
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


def output_dir(root, dirs, files):

	pax = is_multi_rep1(root)  # Are we in something that will be a pax?
	level = get_level(root)  # How far down are we?

	if pax and level == 2:
		# No opex at top level of pax
		return

	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	transfer = ET.SubElement(root_elem, f"{{{opex}}}Transfer")

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
		if is_multi_rep(root, dir):
			# This will be zipped up
			content = ET.SubElement(files_elem, f"{{{opex}}}File", type="content")
			content.text = dir + '.pax.zip'
			create_xip(path.join(root, dir), dir)
			# This describes the zip (how do we otherwise link to catalogue?)
			metadata = ET.SubElement(files_elem, f"{{{opex}}}File", type="metadata")
			metadata.text = dir + '.pax.zip.opex'
			output_pax_file(root, dir + '.pax.zip')
		else:
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
		return None

def output_pax_file(root, file):

	root_elem = ET.Element(f"{{{opex}}}OPEXMetadata")
	filename = path.join(root, file)
	
	output_properties(root_elem, path.basename(root), 2)

	root_tree = ET.ElementTree(element = root_elem)
	indent(root_tree)
	root_tree.write(filename + ".opex")


def output_file(root, file):

	if in_pax(root):
		# Skip opex in pax
		return

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

	indent(root_tree)

	root_tree.write(path.join(folder, item_id + '.xip'))

if len(sys.argv) < 2:
	print("Please provide a directory name")
	sys.exit(1)

source = sys.argv[1]

print(f"Walking directory {source}")

for root, dirs, files in os.walk(source):

	output_dir(root, dirs, files)

	id = path.basename(root)

	for file in files:
		if ignore(file):
			continue
		else:
			output_file(root, file)

print("Finished")