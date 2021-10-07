import matplotlib.tri as tri


def mesh2tri(meshio_mesh):
    """Gets triangulation given mesh.

    Notes:
        Adapted from dolfin source code (avoid dependency).
    """
    cells = meshio_mesh.cells[0]
    if cells.type != 'triangle':
        raise Exception("Only works with triangles")

    xy = meshio_mesh.points
    return tri.Triangulation(xy[:, 0], xy[:, 1], cells.data)
