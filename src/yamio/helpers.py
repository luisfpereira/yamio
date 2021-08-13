
import meshio

from meshio._helpers import extension_to_filetype
from meshio._helpers import _writer_map
from meshio._helpers import reader_map

from yamio.hip import HipReader
from yamio.hip import HipWriter
from yamio.ensight.gold import GeoReader
from yamio.ensight.gold import GeoWriter


extension_to_filetype.update({
    '.geo': 'geo',
    '.mesh.h5': 'hip',
    '.mesh.xmf': 'hip'
})

reader_map.update({
    'geo': GeoReader().read,
    'hip': HipReader().read,
})

_writer_map.update({
    'geo': GeoWriter().write,
    'hip': HipWriter().write,
})


def read(filename, file_format=None):
    return meshio.read(filename, file_format=file_format)


def write(filename, mesh, file_format=None, **kwargs):
    return meshio.write(filename, mesh, file_format=file_format, **kwargs)
