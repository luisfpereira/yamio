
from pathlib import Path

import meshio
from meshio import (
    register_format,
    write,
    extension_to_filetypes,
)

from yamio.hip import (
    HipReader,
    HipWriter,
)
from yamio.ensight.gold import (
    GeoReader,
    GeoWriter,
)


register_format('geo', ['.geo'], GeoReader().read, {'geo': GeoWriter().write})
register_format('hip', ['.mesh.h5', '.mesh.xmf'], HipReader().read,
                {'hip': HipWriter().write})


def read(filename, file_format=None):
    # because meshio _filetypes_from_path does a bad job
    if file_format is None:
        file_formats = extension_to_filetypes.get(''.join(Path(filename).suffixes), [])

        if len(file_formats) == 1:
            file_format = file_formats[0]

    return meshio.read(filename, file_format=file_format)
