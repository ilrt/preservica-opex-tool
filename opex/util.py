from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass
class AssetInfo:
    filename: str
    asset_id: str
    source_path: str
    is_access: bool
    fixity_type: str
    fixity: str
    is_metadata: bool = False


class Dir:

    def __init__(self, name: str = None, dir_id: str = None, parent=None):
        self.parent = parent
        self.name = name
        self.subdirs = {}
        self.files = []
        self.access_files = []
        self.preservation_files = []
        self.dir_id = dir_id

    def add(self, path: list, fileinfo):
        first, *rest = path

        # Two options: simple path a,b,c
        # or (a, a_id), (b, b_id), (c, c_id)
        if type(first) is tuple:
            dirname, dir_id = first
        else:
            dirname = dir_id = first

        if dirname not in self.subdirs:
            self.subdirs[dirname] = Dir(dirname, dir_id, self)

        if rest:
            self.subdirs[dirname].add(rest, fileinfo)
        else:
            self.subdirs[dirname].add_file(fileinfo)

    def add_file(self, fileinfo):
        if fileinfo.is_metadata:
            pass
        elif fileinfo.is_access:
            self.access_files.append(fileinfo)
        else:
            self.preservation_files.append(fileinfo)

        # TODO this is a bit of a hack to ensure the case when there is only one
        # pres or access file works (see 'is_complex')
        self.files.append(fileinfo)

    def all_subdirs(self):
        doing = self.subdirs.items()
        while doing:
            todo = []
            for dirname, dir in doing:
                yield dirname, dir
                todo.extend(dir.subdirs.items())

            doing = todo

    def is_leaf(self):
        return not self.subdirs

    def is_complex(self):
        # If we only have 1 file (of either kind) skip the pax thing
        return len(self.access_files) + len(self.preservation_files) > 1

    def path(self):
        if self.parent:
            return self.parent.path() + '/' + self.name
        else:
            return ''

    def remove_file(self, fileinfo):
        self.files.remove(fileinfo)
        if fileinfo in self.access_files:
            self.access_files.remove(fileinfo)
        if fileinfo in self.preservation_files:
            self.preservation_files.remove(fileinfo)


def elem(ns, tag):
    return ET.Element(f"{{{ns}}}{tag}")


def subelem(parent, ns, tag, text=None, **kwargs):
    elem = ET.SubElement(parent, f"{{{ns}}}{tag}", **kwargs)

    if text:
        elem.text = text

    return elem