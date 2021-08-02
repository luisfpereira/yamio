"""Reads and writes Ensight's gold casefile format.

Notes:
    Still a very naive implementation of a writer and a reader.

    Supports multiple parts and hybrid meshes.

    Validated elements:
        * tri
        * quad


References:
    [1] [EnSight User Manual](https://dav.lbl.gov/archive/NERSC/Software/ensight/doc/Manuals/UserManual.pdf)
"""


import re

import numpy as np

from meshio import Mesh
from meshio import CellBlock


meshio_to_geo_type = {'vertex': 'point',
                      'line': 'bar2',
                      'line3': 'bar3',
                      'triangle': 'tria3',
                      'triangle6': 'tria6',
                      'quad': 'quad4',
                      'quad8': 'quad8',
                      'tetra': 'tetra4',
                      'hexahedron': 'hexa8',
                      'hexahedron20': 'hexa20',
                      'pyramid': 'pyramid5',
                      'pyramid13': 'pyramid13'}
geo_to_meshio_type = {item: key for key, item in meshio_to_geo_type.items()}


# TODO: add test to verify if passed mesh is not modified


class GeoReader:

    def read(self, filename):
        """
        Returns:
            meshio.Mesh or dict: Mesh if only one part or dict of Meshes if more.
        """
        with open(filename, 'r') as file:
            text = file.read()

        parts_text = [part_text for part_text in re.findall(get_part_regex(), text)]
        parts = {}
        for part_text in parts_text:
            name, coords_text, cells_text = part_text
            parts[name] = self._get_part(coords_text, cells_text)

        if len(parts) == 1:
            return parts[list(parts.keys())[0]]
        else:
            return parts

    def _get_part(self, coords_text, cells_text):
        points = self._get_part_coords(coords_text)
        cells = self._get_part_cells(cells_text)
        return Mesh(points, cells)

    def _get_part_coords(self, coords_text):
        return np.array(coords_text.split('\n')[:-1], dtype=float).reshape(3, -1).T

    def _get_part_cells(self, cells_text):
        cells_info, conns = get_conns_regex(with_groups=True)
        regex = re.compile(cells_info + conns)

        cells = []
        for (elem_type, conns_text) in regex.findall(cells_text):
            conns = np.array([elem.split() for elem in conns_text.rstrip().split('\n')], dtype=int)
            cells.append(CellBlock(geo_to_meshio_type[elem_type], conns - 1))

        return cells


class GeoWriter:

    def write(self, filename, mesh, description=None, node_id='off',
              element_id='off', part_description=''):
        '''
        Args:
            mesh (meshio.Mesh or dict of meshio.Mesh): Mesh or part meshes.
                Part description is the key.
            description (array-like, shape=[2]): two initial lines of the file.
            part_description (str): Part description. Ignored if mesh is a `dict`.
        '''
        if type(mesh) is not dict:
            mesh = {part_description: mesh}

        # TODO: add extents
        if description is None:
            description = self._get_default_description()

        # headers
        text = description.copy()
        text.append(f'node id {node_id}')
        text.append(f'node_id {element_id}')

        # write parts
        for i, (part_description, part_mesh) in enumerate(mesh.items()):
            text.extend(self._add_part(i + 1, part_description, part_mesh.points,
                                       part_mesh.cells))

        # write file
        with open(filename, 'w') as file:
            file.write('\n'.join(self._process_text(text)))

    def _get_default_description(self):
        return ['yamio generated file', '']

    def _add_part(self, number, description, coords, cells):
        '''
        Notes:
            * x, y and z coordinates are mandatory, even if 2D.
            * Print order: all x -> all y -> all z.
        '''
        text = ['part', number, description]
        text.extend(self._write_part_coords(coords))

        for cell in cells:
            text.extend(self._write_part_conns(meshio_to_geo_type[cell.type],
                                               cell.data))

        return text

    def _write_part_coords(self, coords):
        n = coords.shape[0]
        if coords.shape[1] < 3:
            coords = np.c_[coords, np.zeros((n,))]

        text = ['coordinates', n]
        for i in range(3):
            text.extend(coords[:, i].tolist())

        return text

    def _write_part_conns(self, elem_type, conns):
        n_elems = conns.shape[0]
        new_conns = conns + 1
        text = [elem_type, n_elems]
        text.extend(new_conns.tolist())

        return text

    def _process_text(self, text):
        return [str(elem) if type(elem) is not list else ' '.join([str(e) for e in elem]) for elem in text]


def get_conns_regex(with_groups=False):
    """
    Notes:
        Function was created to have groups and no-groups regex near, to
        remember to change both simultaneously.

        Need to groups and no-groups are mixed meshes.

        When returning groups, the following groups are returned:
            * elemement type
            * connectivities
    """
    if with_groups:
        cells_info = r'[ ]*(\w+)[ ]*\n[ ]*\d+[ ]*\n'
        conns = r'((?:[0-9 ]{3,}\n*)+)'
    else:
        cells_info = r'[ ]*\w+[ ]*\n[ ]*\d+[ ]*\n'
        conns = r'(?:[0-9 ]{3,}\n*)+'

    return cells_info, conns


def get_part_regex():
    """Gets part regex.

    Starts at part beginning line and stops at the end of coordinates. Retrieves
    the following groups:
        * part description
        * coords
        * cells info (all the text from element type to the end of
        connectivities of last element type)
    """
    part_info = r'[ ]*part[ ]*\n[ ]*[0-9]+[ ]*\n[ ]*(\w+)[ ]*\n(?:.+\n){2}'
    coords = r'([^a-df-zA-DF-Z]+)+'

    cells_info, conns = get_conns_regex(with_groups=False)
    cells_full = rf'((?:{cells_info}{conns})+)'

    return part_info + coords + cells_full
