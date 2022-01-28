
from meshio import (
    register_format,
    read,
    write,
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
