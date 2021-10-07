from collections.abc import Iterable
import copy

import numpy as np
from pyvista.utilities.fileio import from_meshio


def get_pv_mesh(meshio_mesh):
    """Gets pyvista mesh.

    Notes:
        For convenience, mesh is repeated in time series. If memory problems
        raise, then another solution must be found.
    """
    pv_mesh = from_meshio(meshio_mesh)

    # point data
    for var_name, value in meshio_mesh.point_sets.items():
        pv_mesh[var_name] = value

    # cell data
    for var_name, value in meshio_mesh.cell_sets.items():
        pv_mesh[var_name] = value

    return pv_mesh


def get_pv_meshes_timeseries(meshio_mesh):
    """Gets pyvista meshes for timeseries case.

    Notes:
        For convenience, mesh is repeated in time series (even if shared).
        If memory problems raise, then another solution must be found.
    """
    if isinstance(meshio_mesh, Iterable):
        return _get_pv_meshes_timeseries_not_shared(meshio_mesh)
    else:
        return _get_pv_meshes_timeseries_shared(meshio_mesh)


def _get_pv_meshes_timeseries_shared(meshio_mesh):
    times = meshio_mesh.info['time']
    pv_mesh = from_meshio(meshio_mesh)
    pv_meshes = [copy.deepcopy(pv_mesh) for _ in times]

    for i, pv_mesh in enumerate(pv_meshes):
        # point data
        for var_name, value in meshio_mesh.point_sets.items():
            pv_mesh[var_name] = value[i]

        # cell data
        for var_name, value in meshio_mesh.cell_sets.items():
            pv_mesh[var_name] = value[i]

    return times, pv_meshes


def _get_pv_meshes_timeseries_not_shared(meshio_meshes):
    times = np.array([meshio_mesh.info['time'] for meshio_mesh in meshio_meshes])
    pv_meshes = [get_pv_mesh(meshio_mesh) for meshio_mesh in meshio_meshes]

    return times, pv_meshes
