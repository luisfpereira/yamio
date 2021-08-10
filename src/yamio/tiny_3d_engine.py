"""Defines useful tools to play with tiny_3d_engine.

Notes:
    There's not a direct dependency on tiny_3d_engine, but the .geo files are
    created thinking about its particularities.
"""

import meshio


from yamio.mesh_utils import get_local_points_and_cells
from yamio.ensight.gold import GeoWriter

# TODO: wireframe

def write_geo_with_patches(geo_filename, mesh, **kwargs):

    parts = {}
    for patch_name, cell_block in mesh.bnd_patches.items():
        new_points, new_cells = get_local_points_and_cells(mesh.points, [cell_block])
        parts[patch_name] = meshio.Mesh(new_points, new_cells)

    geo_writer = GeoWriter()
    geo_writer.write(geo_filename, parts, **kwargs)
