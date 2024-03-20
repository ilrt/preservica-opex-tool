import importlib.util
import sys
import os
import os.path
from opex.asset_info import Dir, AssetInfo
import opex.opex_generator as opex_generator


def load_module(file_name, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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
                info = conf.get_info_for_file(os.path.join(root, file))

                if info:
                    # We have something to upload
                    to_upload.add(info.target, info)

                    # And also the associated metadata
                    opex_data = opex_generator.output_file(info)
                    opex_filename = info.filename + '.opex'
                    opex_filepath = os.path.join(working_dir, opex_filename)
                    opex_data.write(opex_filepath)
                    opex_info = AssetInfo(opex_filename, None, opex_filepath,
                                          info.target, False, False, None,
                                          None, True)
                    to_upload.add(info.target, opex_info)

    for dirname, dir in to_upload.all_subdirs():
        opex_data = opex_generator.output_dir(dirname,
                                              conf.get_id_for_dir(dirname),
                                              dir.subdirs, dir.files)
        opex_filename = dirname + '.opex'
        opex_filepath = os.path.join(working_dir, opex_filename)
        opex_data.write(opex_filepath)
        opex_info = AssetInfo(opex_filename, None, opex_filepath,
                              info.target, False, False, None, None, True)
        to_upload.add(info.target, opex_info)

    for dirname, dir in to_upload.all_subdirs():
        for filename, fileinfo in dir.files.items():
            print(f"Upload {fileinfo.source_path} to {fileinfo.target}")
