
__version__ = '0.2.0'


from yamio.mesh import Mesh
from yamio._helpers import (
    read,
    write,
)


# TODO: h5cross and other formats
# TODO: yamio xdmf? extend meshio in order to have bdn info
# TODO: from meshio to yamio (get bounds option... how?)