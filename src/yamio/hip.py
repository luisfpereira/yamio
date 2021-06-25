'''Reads and writes Cerfacs' XDMF files by wrapping meshio.

Notes:
    For now it ignores:
        * patches
        * any data
        * mixed elements

    Validated elements:
        * Triangle
        * Quadrilateral
        * Tetrahedron
        * Hexahedron
'''


from xml.etree import ElementTree as ET

import numpy as np
import h5py

from meshio import CellBlock
from meshio import Mesh
from meshio.xdmf.main import XdmfReader
from meshio.xdmf.common import xdmf_to_meshio_type
from meshio.xdmf.common import meshio_to_xdmf_type

from yamio.xdmf2_utils import create_root
from yamio.xdmf2_utils import create_topology_section
from yamio.xdmf2_utils import create_geometry_section
from yamio.xdmf2_utils import create_h5_dataset


class HipReader(XdmfReader):
    # TODO: add support for patches

    def __init__(self):
        pass
        # self.filename = filename
        # self.h5_filename = h5_filename
        # if h5_filename is None:
        #     self.h5_filename = f"{'.'.join(filename.split('.')[:-1])}.h5"

    def _get_etree(self, filename):

        parser = ET.XMLParser()
        tree = ET.parse(filename, parser)

        return tree

    def _get_topology(self, topology_elem):

        cells = []
        data_item = list(list(topology_elem)[0])[0]

        topology_type = topology_elem.get("Type")
        n_elems = int(topology_elem.get('NumberOfElements'))
        size = int(data_item.get('Dimensions'))
        data = self._read_data_item(data_item).reshape(-1, size // n_elems)

        # correct data
        data = correct_cell_conns_reading.get(topology_type, lambda x: x)(data)
        data -= 1  # correct initial index
        cells.append(CellBlock(xdmf_to_meshio_type[topology_type], data))

        return cells

    def _get_geometry(self, geometry_elem):
        return np.array([self._read_data_item(data_item) for data_item in list(geometry_elem)]).T

    def read(self, filename, h5_filename=None):
        '''
        Notes:
            Assumes first grid is the mesh and ignores patches.
        '''
        self.filename = filename  # bad code, but forced by inheritance
        if h5_filename is None:
            h5_filename = f"{'.'.join(filename.split('.')[:-1])}.h5"

        tree = self._get_etree(filename)

        topology_elem = tree.find('.//Topology')
        cells = self._get_topology(topology_elem)

        geometry_elem = tree.find('.//Geometry')
        points = self._get_geometry(geometry_elem)

        with h5py.File(h5_filename, 'r') as h5_file:
            boundary = Boundary.read_from_h5(h5_file)

        return HipMesh(points, cells, boundary)


class HipWriter:

    def __init__(self):
        self.version = '2.0'
        self.fmt = 'HDF'

    def write(self, file_basename, mesh):
        root = create_root(version=self.version, Format=self.fmt)
        domain = ET.SubElement(root, "Domain")
        # TODO: need more parameters here?
        grid = ET.SubElement(domain, "Grid", Name="Grid")

        with h5py.File(f'{file_basename}.mesh.h5', 'w') as h5_file:

            # write mesh topology
            self._write_topology(h5_file, mesh, grid)

            # write mesh geometry
            self._write_geometry(h5_file, mesh, grid)

            # write boundary data (only in h5 file)
            mesh.boundary.write_to_h5(h5_file)

        # dump tree
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        tree.write(f'{file_basename}.mesh.xmf', xml_declaration=True,
                   encoding='utf-8')

        return tree

    def _write_topology(self, file, mesh, grid_elem):
        # ignores mixed case
        topology_type = meshio_to_xdmf_type[mesh.cells[0].type][0]
        data = mesh.cells[0].data
        data = correct_cell_conns_writing.get(topology_type, lambda x: x)(data)
        data += 1
        return create_topology_section(grid_elem, data, file,
                                       topology_type, Format=self.fmt)

    def _write_geometry(self, file, mesh, grid_elem):
        return create_geometry_section(grid_elem, mesh.points, file,
                                       Format=self.fmt)


def _correct_tetrahedron_conns_reading(cells):
    cells[:, [1, 2]] = cells[:, [2, 1]]
    return cells


def _correct_tetrahedron_conns_writing(cells):
    cells[:, [2, 1]] = cells[:, [1, 2]]
    return cells


correct_cell_conns_reading = {'Tetrahedron': _correct_tetrahedron_conns_reading}

correct_cell_conns_writing = {'Tetrahedron': _correct_tetrahedron_conns_writing}


class HipMesh(Mesh):

    def __init__(self, points, cells, boundary, point_data=None, cell_data=None,
                 field_data=None, point_sets=None, cell_sets=None,
                 gmsh_periodic=None, info=None):
        super().__init__(points, cells, point_data=point_data,
                         cell_data=cell_data, field_data=field_data,
                         point_sets=point_sets, cell_sets=cell_sets,
                         gmsh_periodic=gmsh_periodic, info=info)
        self.boundary = boundary


class Boundary:
    # for h5
    label_nodes = 'Boundary/bnode->node'
    label_groups = 'Boundary/bnode_lidx'

    def __init__(self, nodes, group_dims):
        # TODO: add patch labels? (they have to be handled differently)
        self.nodes = nodes
        self.group_dims = group_dims

    @classmethod
    def read_from_h5(cls, h5_file):
        nodes = cls._read_dataset(h5_file, cls.label_nodes) - 1
        group_dims = cls._read_dataset(h5_file, cls.label_groups) - 1

        return Boundary(nodes, group_dims)

    @staticmethod
    def _read_dataset(h5_file, label):
        return h5_file[label][()]

    def write_to_h5(self, h5_file):
        create_h5_dataset(h5_file, self.label_nodes, self.nodes + 1)
        create_h5_dataset(h5_file, self.label_groups, self.group_dims + 1)
