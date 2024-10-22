# Example configuration file
from opex.util import AssetInfo
from os.path import exists


# In this example we will assume that assets are files named:
#
# parent_name++child_name.ext
#
# Where ext might be:
#
#   * tif, raw - masters for preservation
#   * jpg, png - access versions
#   * md5      - not an asset, but hash of an asset which sits next to asset
#
# Additionally parent and child are written 'x-y-z', but the
# catalogue uses '/' as the divider, so id is 'x/y/z'

# For the upload tool, target container for uploads
CONTAINER = 'example_container'


def path_to_parts(path):
    # Break path into bits and return them
    # TODO
    return parent_name, asset_name, ext


# Replace '-' with '/' to get a catalogue id
def id_to_catalogue_id(id):
    return re.sub('-', '/', id)


# For each visited file, this function will be called
def get_info_for_file(path):

    match = GET_ID_EXT.search(path)

    # If this file isn't an asset return None, None
    if not match:
        return None, None

    parent, asset_name, ext = path_to_parts(path)

    if ext in ['md5']:
        # Ignore, not an asset but looks like one
        return None, None

    # Is there an md5 file for this asset?
    md5file = path.replace(ext, 'md5')

    # If so set type and read content into 'fixity'
    if exists(md5file):
        fixity_type = 'MD5'
        fixity = open(md5file, 'r').read()
    else:
        fixity_type = None
        fixity = None

    # This is where the asset will be uploaded to
    # It can either be a simple array [parent, child]
    # Or more complex if id of item differs from name
    # e.g. [(parent_name, parent_id), (child_name, child_id)]
    target = [(name, id_to_catalogue_id(name)) for name in [parent, asset_id]]

    info = AssetInfo(
        filename=asset_name + '.' + ext,  # Filename to upload as
        asset_id=to_calm_id(asset_name),  # Id of the asset
        source_path=path,                 # Where this asset lives. DON'T CHANGE THIS!
        is_access=ext in ['jpg', 'png'],  # These extensions are our access types
        fixity_type=fixity_type,          # See above for where we got these
        fixity=fixity
    )

    return target, info  # Path (as array) where asset will be uploaded to, and asset info
