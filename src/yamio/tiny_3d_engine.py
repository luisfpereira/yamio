"""Defines useful tools to play with tiny_3d_engine.

Notes:
    There's not a direct dependency on tiny_3d_engine, but the .geo files are
    created thinking about its particularities.
"""

import meshio


from yamio.mesh_utils import get_local_points_and_cells
from yamio.mesh_utils import get_brep
from yamio.ensight.gold import GeoWriter

# TODO: go directly from mesh


def write_geo_with_patches(geo_filename, mesh, brep=False, **kwargs):
    """
    Args:
        geo_filename (str)
        mesh (HipMesh): Mesh object with patches.
    """
    # TODO: verify 2d case with brep (it is already 1d)

    parts = {}
    for patch_name, cell_block in mesh.bnd_patches.items():
        new_points, new_cells = get_local_points_and_cells(mesh.points, [cell_block])

        if brep:
            new_points, new_cells = get_brep(new_points, new_cells)

        parts[patch_name] = meshio.Mesh(new_points, new_cells)

    geo_writer = GeoWriter()
    geo_writer.write(geo_filename, parts, **kwargs)
