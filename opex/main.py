import importlib.util
import os
import argparse
import os.path
from opex.util import Dir, AssetInfo, load_module, pick_name
import opex.opex_generator as opex_generator
import opex.pax_generator as pax_generator
import logging


logger = logging.getLogger(__name__)


def main(argv):
    argv.pop(0)  # why do I need this?

    parser = argparse.ArgumentParser(prog='to_opex',
                                     description='Tool to prepare collections for import to preservica')
    parser.add_argument('-c', '--config', required=True, help='Config file')
    parser.add_argument('-t', '--target', required=True, help='Target folder')
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
                    logger.debug(f"File will be uploaded: {file} (Access? {info.is_access})")
                    to_upload.add(target, info)
                else:
                    logger.debug(f"Ignoring file: {file}")

    # We go through subdirs in reverse order (bottom up)
    # to ensure dir opex is present in parent
    for dirname, dir in to_upload.all_subdirs(top_down=False):
        logger.debug(f"Making opexes and paxes for {dir}")

        dir_contents = list(dir.files.items())  # defensive copy

        for asset_id, files in dir_contents:

            if not asset_id:
                logger.warn(f'Skipping non-asset files: {files}')

            if len(files) > 1:  # More than one file has this asset id
                logger.debug(f"{asset_id} in dir {dir.name} has more than one file and needs to be a pax")
                # We will generate a pax
                pax_prefix = pick_name(asset_id, files)  # name pax based on filenames or id
                pax_filename = pax_prefix + '.pax.zip'
                zip_path = os.path.join(target_dir, pax_filename)
                pax_generator.create_pax(asset_id, files, zip_path, pax_prefix, dry_run)

                # Files are now all in the pax zip, so we remove them from the dir
                dir.files.pop(asset_id)

                # And now add the pax file to replace them
                pax_info = AssetInfo(pax_filename, asset_id, zip_path,
                                    False, None, None, False)
                dir.add_file(pax_info)

                opex_data = opex_generator.output_file(pax_info, conf)
                opex_filename = pax_info.filename + '.opex'
                opex_filepath = os.path.join(target_dir, opex_filename)
                opex_data.write(opex_filepath)
                opex_info = AssetInfo(opex_filename, None, opex_filepath,
                                    False, None, None, True)
                dir.add_file(opex_info)
            else:
                logger.debug(f"{asset_id} in dir {dir.name} doesn't need a pax")

                info = files[0]  # only 1 file with this id
                logger.debug(f"Sole file for asset {asset_id}: {info.filename}")
                opex_data = opex_generator.output_file(info, conf)
                opex_filename = info.filename + '.opex'
                opex_filepath = os.path.join(target_dir, opex_filename)
                opex_data.write(opex_filepath)
                opex_info = AssetInfo(opex_filename, None, opex_filepath,
                                    False, None, None, True)
                dir.add_file(opex_info)

        # Now create opex for dir

        if dir.parent:
            opex_filename = dirname + '.opex'
        else:
            # We are creating an opex for the root
            # Call it 'root.opex'
            opex_filename = 'root.opex'

        logger.debug(f"Making opex for dir {dirname}")
        opex_data = opex_generator.output_dir(dir, conf)
        opex_filename = opex_filename
        opex_filepath = os.path.join(target_dir, opex_filename)
        opex_data.write(opex_filepath)
        opex_info = AssetInfo(opex_filename, None, opex_filepath,
                              False, None, None, True)

        logger.debug(f"Adding {opex_filename} to {dir}")
        dir.add_file(opex_info)

    uploads_file = os.path.join(target_dir, "to_upload.txt")

    with open(uploads_file, "w") as f:
        for dirname, dir in to_upload.all_subdirs():
            for asset_id, files in dir.files.items():
                for fileinfo in files:
                    f.write(fileinfo.source_path)
                    f.write("\t")
                    f.write(dir.path() + '/' + fileinfo.filename)
                    f.write('\n')

    print(f"Upload list is: {uploads_file}")
