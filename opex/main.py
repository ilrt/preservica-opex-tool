import importlib.util
import sys
import os
import argparse
import os.path
from opex.util import Dir, AssetInfo
import opex.opex_generator as opex_generator
import opex.pax_generator as pax_generator
import logging


logger = logging.getLogger(__name__)


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
        pax_items.append(fileinfo)
        del files[filename]  # Remove this file, it will be part of zip

    if not pax_items:
        return

    # Make in memory pax xml

    # Make zip containing files and pax xml in working dir

    # Add pax to files


def main(argv):
    argv.pop(0)  # why do I need this?

    parser = argparse.ArgumentParser(prog='to_opex',
                                     description='Tool to prepare collections for import to preservica')
    parser.add_argument('config', help='Config file')
    parser.add_argument('target', help='Target folder')
    parser.add_argument('source', nargs='+', help='Source folder(s)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Explain what is happening')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help="Don't actually perform any actions, for testing")

    arguments = parser.parse_args(argv)

    conf_file = arguments.config
    sources = arguments.source
    verbose = arguments.verbose
    dry_run = arguments.dry_run
    target_dir = arguments.target

    print(f"conf_file: {conf_file}")
    print(f"sources: {', '.join(sources)}")
    print(f"verbose: {verbose}")
    print(f"dry_run: {dry_run}")
    print(f"target_dir: {target_dir}")

    format = '%(levelname)s\t%(message)s'
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format=format)
    else:
        logging.basicConfig(level=logging.INFO, format=format)

    logger.debug(f"Loading config file: {conf_file}")
    conf = load_module(conf_file, "opex_config")

    if not os.path.exists(target_dir):
        logger.info(f'Creating target directory: {target_dir}')
        os.makedirs(target_dir)

    to_upload = Dir()

    for source in sources:
        logger.debug(f"In source {source}")
        for root, dirs, files in os.walk(source):

            for file in files:
                target, info = conf.get_info_for_file(os.path.join(root, file))

                if info:
                    # We have something to upload
                    logger.debug(f"File will be uploaded: {file}")
                    to_upload.add(target, info)

    for dirname, dir in to_upload.all_subdirs():

        opex_data = opex_generator.output_dir(dir)
        opex_filename = dirname + '.opex'
        opex_filepath = os.path.join(target_dir, opex_filename)
        opex_data.write(opex_filepath)
        opex_info = AssetInfo(opex_filename, None, opex_filepath,
                              False, None, None, True)
        dir.add_file(opex_info)

        if dir.is_complex():
            logger.debug(f"Dir {dir.name} has more than one file and needs to be a pax")
            # We will generate a pax
            pax_filename = dir.name + '.pax.zip'
            zip_path = os.path.join(target_dir, pax_filename)
            pax_generator.create_pax(dir, zip_path, dry_run)

            pax_info = AssetInfo(pax_filename, None, zip_path,
                                 False, None, None, False)
            dir.add_file(pax_info)

            opex_data = opex_generator.output_file(pax_info)
            opex_filename = pax_info.filename + '.opex'
            opex_filepath = os.path.join(target_dir, opex_filename)
            opex_data.write(opex_filepath)
            opex_info = AssetInfo(opex_filename, None, opex_filepath,
                                  False, None, None, True)
            dir.add_file(opex_info)
        else:
            logger.debug(f"Dir {dir.name} doesn't need a pax")
            # TODO: this is dodgy. We want to ignore metadata files
            # Ideally get non-metadata file list (possibly empty)
            info = dir.files[0]
            if not info.is_metadata:
                logger.debug(f"Sole file for dir: {info.filename}")
                opex_data = opex_generator.output_file(info)
                opex_filename = info.filename + '.opex'
                opex_filepath = os.path.join(target_dir, opex_filename)
                opex_data.write(opex_filepath)
                opex_info = AssetInfo(opex_filename, None, opex_filepath,
                                      False, None, None, True)
                dir.add_file(opex_info)

    uploads_file = os.path.join(target_dir, "to_upload.txt")

    with open(uploads_file, "w") as f:
        for dirname, dir in to_upload.all_subdirs():
            for fileinfo in dir.files:
                f.write(fileinfo.source_path)
                f.write("\t")
                f.write(dir.path() + '/' + fileinfo.filename)
                f.write('\n')

    print(f"Upload list is: {uploads_file}")
