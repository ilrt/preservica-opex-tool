# franko b config
from opex.util import AssetInfo
import re
from os.path import exists

GET_ID_EXT = re.compile(r'((FB(?:-\d+)+)-\d\d\d+)\.([0-9a-zA-Z_]+)$')

CONTAINER = 'opex_wildfilm'

VIRTUAL_LEAF_DIR = True

def to_calm_id(name):
    # CALM ids user forward slash, not dash
    return re.sub('-', '/', name)


def get_info_for_file(path):

    match = GET_ID_EXT.search(path)

    if not match:
        return None, None

    parent, asset_id, ext = match.group(2), match.group(1), match.group(3)

    if ext in ['md5']:
        # Not a file type we care about
        return None, None

    md5file = path.replace(ext, 'md5')

    if exists(md5file):
        fixity_type = 'MD5'
        fixity = open(md5file, 'r').read()
    else:
        fixity_type = None
        fixity = None

    # Map names to ids
    target = [(name, to_calm_id(name)) for name in [parent]]

    info = AssetInfo(
        filename=asset_id + '.' + ext,
        asset_id=to_calm_id(asset_id),
        source_path=path,
        is_access="Preservica_access" in path,
        fixity_type=fixity_type,
        fixity=fixity
    )

    return target, info
