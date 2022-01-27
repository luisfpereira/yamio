
from meshio import (
    register_format,
    read,
    write,
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
