import importlib.util
import sys
import os
import os.path
from opex.util import Dir, AssetInfo
import opex.opex_generator as opex_generator
import opex.pax_generator as pax_generator


def load_module(file_name, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Find files which are access or preservation copies
# and make a pax
def collect_pax_items(files):
    pax_items = []
    for filename, fileinfo in files:
        if fileinfo.is_access or fileinfo.is_preservation:
            pax_items.append(fileinfo)
            del files[filename]  # Remove this file, it will be part of zip

    if not pax_items:
        return

    # Make in memory pax xml

    # Make zip containing files and pax xml in working dir

    # Add pax to files


def main(argv):
    if len(argv) < 3:
        print(f"Usage: {argv[0]} conf source_dirs+")
        sys.exit(1)

    conf_file = argv[1]
    sources = argv[2:]

    conf = load_module(conf_file, "opex_config")

    to_upload = Dir()

    working_dir = conf.working_dir

    for source in sources:
        print(f"in source {source}")
        for root, dirs, files in os.walk(source):

            for file in files:
                target, info = conf.get_info_for_file(os.path.join(root, file))

                if info:
                    # We have something to upload
                    to_upload.add(target, info)

                    # And also the associated metadata if this is a 
                    # 'simple' asset (no versions)
                    if info.is_simple():
                        opex_data = opex_generator.output_file(info)
                        opex_filename = info.filename + '.opex'
                        opex_filepath = os.path.join(working_dir, opex_filename)
                        opex_data.write(opex_filepath)
                        opex_info = AssetInfo(opex_filename, None, opex_filepath,
                                              False, False, None, None, True)
                        to_upload.add(target, opex_info)

    for dirname, dir in to_upload.all_subdirs():

        opex_data = opex_generator.output_dir(dir)
        opex_filename = dirname + '.opex'
        opex_filepath = os.path.join(working_dir, opex_filename)
        opex_data.write(opex_filepath)
        opex_info = AssetInfo(opex_filename, None, opex_filepath,
                              False, False, None, None, True)
        dir.add_file(opex_info)

        if dir.is_complex():
            # We will generate a pax
            pax_filename = dir.name + '.pax.zip'
            zip_path = os.path.join(working_dir, pax_filename)
            pax_generator.create_pax(dir, zip_path)

            pax_info = AssetInfo(pax_filename, None, zip_path, None,
                                 False, None, None, False)

            dir.add_file(pax_info)

            opex_data = opex_generator.output_file(pax_info)
            opex_filename = pax_info.filename + '.opex'
            opex_filepath = os.path.join(working_dir, opex_filename)
            opex_data.write(opex_filepath)
            opex_info = AssetInfo(opex_filename, None, opex_filepath,
                                  False, False, None, None, True)

            dir.add_file(opex_info)

    uploads_file = os.path.join(working_dir, "to_upload.txt")

    with open(uploads_file, "w") as f:
        for dirname, dir in to_upload.all_subdirs():
            for fileinfo in dir.files:
                f.write(fileinfo.source_path)
                f.write("\t")
                f.write(dir.path() + '/' + fileinfo.filename)
                f.write('\n')

    print(f"Upload list is: {uploads_file}")
