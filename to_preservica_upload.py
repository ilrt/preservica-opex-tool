import os
import sys
import re
import opex
import zipfile
import xml.etree.ElementTree as ET


def right_type(ext):
	# Very liberal currently
	return ext not in ['md5']


GET_ID_EXT = re.compile(r'((FB(?:-\d+)+)-\d\d\d+)\.([0-9a-zA-Z_]+)$')


def get_id(filename):
	match = GET_ID_EXT.search(filename)
	if match:
		return match.group(2), match.group(1), match.group(3)
	else:
		return None, None, None


def get_target_dir(target, root, parent, asset):
	# If we're in a multirep dir tack on relevant bottom dir
	if "Preservica_preservation" in root:
		asset = asset + '.pax.zip'
		return 'Representation_Preservation', \
			os.path.join(target, parent, asset), True
	elif "Preservica_presentation" in root:
		asset = asset + '.pax.zip'
		return 'Representation_Access', \
			os.path.join(target, parent, asset), False
	else:
		return os.path.join(target, parent, asset), None, None


def list_dir(dir):
	files = []
	dirs = []

	for entry in os.scandir(dir):
		if entry.is_dir():
			dirs.append(entry.name)
		elif entry.is_file():
			files.append(entry.name)

	return files, dirs



def main(argv):

	if len(argv) < 3:
		print(f"Usage: {argv[0]} target_dir source_dirs+")
		sys.exit(1)

	target = argv[1]
	sources = argv[2:]

	print(f"Flatten {sources} to {target}")

	opex_dirs = { target: 0 } # level 0 entry
	pax_zips = {}

	for source in sources:
		for root, dirs, files in os.walk(source):
			print(f"in {root}")
	
			# Change: 
			# Look at each file
			# Check whether extension is something we are interested in
			# If so check whether id in list of things to transfer
			# If all correct:
			# Get parent id and asset id from root
			# See whether preservation or access in there
			# At this point make dir tree and link file
			# Doesn't cover case where pres and access are siblings
			
			for file in files:
	
				parent, asset_id, file_ext = get_id(file)
				
				if asset_id and right_type(file_ext):
	
					targetdir, paxdir, is_preserve = get_target_dir(target, root, parent, asset_id)

					sourcedir = os.path.relpath(root, targetdir)
	
					if paxdir:
						if paxdir not in pax_zips:
							os.makedirs(os.path.dirname(paxdir), exist_ok=True)  # ensure parent dir storing zip exists
							zip = zipfile.ZipFile(paxdir, mode='x', compression=zipfile.ZIP_STORED, compresslevel=None)
							entries = []
							pax_zips[paxdir] = (zip, entries, asset_id)
						else:
							zip, entries, asset_id_stored = pax_zips[paxdir]
						print(root, file)
						zip.write(os.path.join(root, file), arcname=os.path.join(targetdir, file))
						entries.append((os.path.join(root, file), os.path.join(targetdir, file), is_preserve))
					else:
						os.makedirs(targetdir, exist_ok=True)  # ensure target exists
						# symlink to original
						# is there a nicer way to make this relative link?
						cwd = os.getcwd()
						os.chdir(targetdir)
						os.symlink(os.path.join(sourcedir, file), file)
						os.chdir(cwd)
						opex_dirs[targetdir] = 2  # Bottom level dir
	
					opex_dirs[os.path.join(target, parent)] = 1  # Virtual

	# Complete zip/pax with xip description and close
	for zip, entries, asset_id in pax_zips.values():
		xip = opex.create_xip(asset_id, entries)
		zip.writestr(asset_id + '.xip', ET.tostring(xip.getroot()))
		zip.close()

	# Finally generate opex files
	for opex_dir, level in opex_dirs.items():
		files, dirs = list_dir(opex_dir)
		for file in files:
			opex.output_file(opex_dir, file)

		opex.output_dir(opex_dir, dirs, files, level)


if __name__=="__main__":
	main(sys.argv)