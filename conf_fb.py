# franko b config
from opex.asset_info import AssetInfo
import re
from os.path import exists

GET_ID_EXT = re.compile(r'((FB(?:-\d+)+)-\d\d\d+)\.([0-9a-zA-Z_]+)$')

working_dir = 'working'


def to_calm_id(name):
    # CALM ids user forward slah, not dash
    return re.sub('-', '/', name)


def get_id_for_dir(dir):
    return to_calm_id(dir)


def get_info_for_file(path):

    match = GET_ID_EXT.search(path)

    if not match:
        return None

    parent, asset_id, ext = match.group(2), match.group(1), match.group(3)

    if ext in ['md5']:
        # Not a file type we care about
        return None

    md5file = path.replace(ext, 'md5')

    if exists(md5file):
        fixity_type = 'MD5'
        fixity = open(md5file, 'r').read()
    else:
        fixity_type = None
        fixity = None

    info = AssetInfo(
        filename=asset_id + '.' + ext,
        asset_id=to_calm_id(asset_id),
        source_path=path,
        target=[parent, asset_id],
        is_access="Preservica_access" in path,
        is_preservation="Preservica_presentation" in path,
        fixity_type=fixity_type,
        fixity=fixity
    )

    return info
