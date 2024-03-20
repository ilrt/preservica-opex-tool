from dataclasses import dataclass


@dataclass
class AssetInfo:
    filename: str
    asset_id: str
    source_path: str
    target: object
    is_access: bool
    is_preservation: bool
    fixity_type: str
    fixity: str
    is_metadata: bool = False


class Dir:

    def __init__(self, name: str = None):
        self.name = name
        self.subdirs = {}
        self.files = {}

    def add(self, path, file):
        first, *rest = path

        if not rest:
            self.files[file.filename] = file
            return

        if first not in self.subdirs:
            self.subdirs[first] = Dir(first)

        self.subdirs[first].add(rest, file)

    def all_subdirs(self):
        doing = self.subdirs.items()
        while doing:
            todo = []
            for dirname, dir in doing:
                yield dirname, dir
                todo.extend(dir.subdirs.items())

            doing = todo
