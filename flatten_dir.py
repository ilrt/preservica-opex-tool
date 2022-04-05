import os
import sys
import re
import opex

def need_transfer(files):
	for filename in files:
		if filename in for_transfer:
			return True
	return False


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
		asset = asset + '.pax'
		return os.path.join(target, parent, asset, 'Representation_Preservation'), \
			os.path.join(target, parent, asset)
	elif "Preservica_presentation" in root:
		asset = asset + '.pax'
		return os.path.join(target, parent, asset, 'Representation_Access'), \
			os.path.join(target, parent, asset)
	else:
		return os.path.join(target, parent, asset), None


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

	if len(argv) < 4:
		print("Usage: flatten_dir target_dir transfer_file source_dirs*")
		sys.exit(1)

	source = argv[1]
	target = argv[1]
	transfer_file = argv[2]
	sources = argv[3:]

	global for_transfer

	with open(transfer_file) as tf:
		for_transfer = set(line.rstrip() for line in tf.readlines())

	print(f"Flatten {sources} to {target}")

	opex_dirs = { target: 0 } # level 0 entry
	pax_dirs = set()


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
	
					targetdir, paxdir = get_target_dir(target, root, parent, asset_id)
	
					os.makedirs(targetdir, exist_ok=True)
	
					sourcedir = os.path.relpath(root, targetdir)
	
					# is there a nicer way to make this relative link?
					cwd = os.getcwd()
					os.chdir(targetdir)
					os.symlink(os.path.join(sourcedir, file), file)
					os.chdir(cwd)
	
					if paxdir:
						pax_dirs.add(paxdir)
					else:
						opex_dirs[targetdir] = 2  # Bottom level dir
	
					opex_dirs[os.path.join(target, parent)] = 1  # Virtual

	for opex_dir, level in opex_dirs.items():

		files, dirs = list_dir(opex_dir)

		for file in files:
			opex.output_file(opex_dir, file)

		opex.output_dir(opex_dir, dirs, files, level)

	for pax_dir in pax_dirs:
		print(f"Pax:  {pax_dir}")




if __name__=="__main__":
	main(sys.argv)