from dataclasses import dataclass
import xml.etree.ElementTree as ET
import importlib.util
import sys
import logging


logger = logging.getLogger(__name__)


def load_module(file_name, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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
        self.dir_id = dir_id

    def __str__(self):
        return f"<DIR {self.name} [{id(self)}]>"

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
        self.files.append(fileinfo)

    def all_subdirs(self, top_down=True):
        if top_down:  # Visit this first
            yield self.name, self

        for name, dir in self.subdirs.items():
            yield from dir.all_subdirs(top_down=top_down)

        if not top_down:  # Visit this after descendants
            yield self.name, self

    def is_leaf(self):
        return not self.subdirs

    def is_complex(self):
        # If we only have 1 file (of either kind) skip the pax thing
        return len(self.asset_files()) > 1

    def path(self):
        if self.parent:
            return self.parent.path() + '/' + self.name
        else:
            return ''

    def remove_file(self, fileinfo):
        self.files.remove(fileinfo)

    def access_files(self):
        return [f for f in self.files if f.is_access and not f.is_metadata]

    def preservation_files(self):
        return [f for f in self.files if not f.is_access and not f.is_metadata]

    def asset_files(self):
        return [f for f in self.files if not f.is_metadata]

    def print_tree(self):
        pass



def elem(ns, tag):
    return ET.Element(f"{{{ns}}}{tag}")


def subelem(parent, ns, tag, text=None, **kwargs):
    elem = ET.SubElement(parent, f"{{{ns}}}{tag}", **kwargs)

    if text:
        elem.text = text

    return elem