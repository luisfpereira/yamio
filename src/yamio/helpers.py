
import meshio

from meshio._helpers import extension_to_filetype
from meshio._helpers import _writer_map

from yamio.hip import HipWriter
from yamio.ensight.gold import GeoWriter


extension_to_filetype.update({
    '.geo': 'geo',
    '.mesh.h5': 'hip'
})

_writer_map.update({
    'geo': GeoWriter().write,
    'hip': HipWriter().write,
})


def write(filename, mesh, file_format=None, **kwargs):
    return meshio.write(filename, mesh, file_format=file_format, **kwargs)
