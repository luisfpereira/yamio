
from pathlib import Path

import meshio
from meshio import (
    register_format,
    write,
    extension_to_filetypes,
)

from yamio.ensight.gold import (
    GeoReader,
    GeoWriter,
)


try:
    import pyhip
    has_pyhip = True
except ImportError:
    has_pyhip = False

try:
    import h5py
    has_h5py = True
except ImportError:
    has_h5py = False


# TODO: writer for hip is not following the right flow...


register_format('geo', ['.geo'], GeoReader().read, {'geo': GeoWriter().write})


if has_pyhip and has_h5py:
    from yamio.hip import (
        HipReader,
        HipWriter,
    )

    register_format('hip', ['.mesh.h5', '.mesh.xmf'], HipReader().read,
                    {'hip': HipWriter().write})


if has_h5py:
    from yamio.dolfin import write as write_dolfin

    register_format('dolfin-yamio', [], None, {'dolfin-yamio': write_dolfin})


def read(filename, file_format=None):
    # because meshio _filetypes_from_path does a bad job
    if file_format is None:
        file_formats = extension_to_filetypes.get(''.join(Path(filename).suffixes), [])

        if len(file_formats) == 1:
            file_format = file_formats[0]

    return meshio.read(filename, file_format=file_format)


