from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass
class AssetInfo:
    filename: str
    asset_id: str
    source_path: str
    is_access: bool
    is_preservation: bool
    fixity_type: str
    fixity: str
    is_metadata: bool = False

    def is_simple(self):
        return not (self.is_access or self.is_preservation)


@dataclass
class DirInfo:
    dirname: str
    dir_id: str

    def __init__(self, dirname: str, dir_id: str = None):
        if not dir_id:
            dir_id = dirname
        self.dir_id = dir_id
        self.dirname = dirname


class Dir:

    def __init__(self, name: str = None, dir_id: str = None, parent = None):
        self.parent = parent
        self.name = name
        self.subdirs = {}
        self.files = []
        self.access_files = []
        self.preservation_files = []
        self.dir_id = dir_id

    def add(self, path: list[DirInfo], fileinfo):
        first, *rest = path

        if first.dirname not in self.subdirs:
            self.subdirs[first.dirname] = Dir(first.dirname, first.dir_id,
                                              self)

        if rest:
            self.subdirs[first.dirname].add(rest, fileinfo)
        else:
            self.subdirs[first.dirname].add_file(fileinfo)

    def add_file(self, fileinfo):
        if fileinfo.is_preservation:
            self.preservation_files.append(fileinfo)
        elif fileinfo.is_access:
            self.access_files.append(fileinfo)
        else:
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
        return self.access_files or self.preservation_files

    def path(self):
        if self.parent:
            return self.parent.path() + '/' + self.name
        else:
            return ''


def elem(ns, tag):
    return ET.Element(f"{{{ns}}}{tag}")


def subelem(parent, ns, tag, text=None, **kwargs):
    elem = ET.SubElement(parent, f"{{{ns}}}{tag}", **kwargs)

    if text:
        elem.text = text

    return elem