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
from meshio._common import num_nodes_per_cell
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

        topology_type = xdmf_to_meshio_type[topology_elem.get("Type")]
        n_nodes_cell = num_nodes_per_cell[topology_type]

        data_item = list(list(topology_elem)[0])[0]

        data = self._read_data_item(data_item).reshape(-1, n_nodes_cell)

        return self._get_corrected_cells(data, topology_type)

    def _get_patch_topology(self, topology_elem):

        topology_type = xdmf_to_meshio_type[topology_elem.get("Type")]
        n_nodes_cell = num_nodes_per_cell[topology_type]

        data_item_parent = list(list(topology_elem)[0])[0]

        # get indices
        data_item = list(data_item_parent)[0]
        init, _, size = [int(num) for num in data_item.text.split()]
        end = init + size

        # get data
        data_item = list(data_item_parent)[1]
        data = self._read_data_item(data_item)[init:end].reshape(-1, n_nodes_cell)

        return self._get_corrected_cells(data, topology_type)

    def _get_corrected_cells(self, data, topology_type):

        data = correct_cell_conns_reading.get(topology_type, lambda x: x)(data)
        data -= 1  # correct initial index
        cells = [CellBlock(topology_type, data)]

        return cells

    def _get_geometry(self, geometry_elem):
        return np.array([self._read_data_item(data_item) for data_item in list(geometry_elem)]).T

    def _get_patches(self, tree):
        topology_elems = tree.findall('.//Topology')

        patches = [self._get_patch_topology(topology_elem)[0] for topology_elem in topology_elems[1:]]

        return patches

    def read(self, filename, h5_filename=None):
        '''
        Notes:
            Assumes first grid is the mesh and ignores patches.
        '''
        self.filename = filename  # bad code, but forced by inheritance
        if h5_filename is None:
            h5_filename = f"{'.'.join(filename.split('.')[:-1])}.h5"

        tree = self._get_etree(filename)

        # assumes first topology is mesh
        topology_elem = tree.find('.//Topology')
        cells = self._get_topology(topology_elem)

        geometry_elem = tree.find('.//Geometry')
        points = self._get_geometry(geometry_elem)

        patches = self._get_patches(tree)

        with h5py.File(h5_filename, 'r') as h5_file:
            boundary = Boundary.read_from_h5(h5_file)

        return HipMesh(points, cells, boundary, patches=patches)


class HipWriter:

    def __init__(self):
        self.version = '2.0'
        self.fmt = 'HDF'

    def write(self, file_basename, mesh, write_bnd=False):
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
            if write_bnd:
                mesh.boundary.write_to_h5(h5_file)

        # dump tree
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        tree.write(f'{file_basename}.mesh.xmf', xml_declaration=True,
                   encoding='utf-8')

        return tree

    def _write_topology(self, file, mesh, grid_elem):
        # ignores mixed case
        topology_type = mesh.cells[0].type
        data = mesh.cells[0].data
        data = correct_cell_conns_writing.get(topology_type, lambda x: x)(data)
        data += 1
        return create_topology_section(grid_elem, data, file,
                                       meshio_to_xdmf_type[topology_type][0],
                                       Format=self.fmt)

    def _write_geometry(self, file, mesh, grid_elem):
        return create_geometry_section(grid_elem, mesh.points, file,
                                       Format=self.fmt)


def _correct_tetra_conns_reading(cells):
    cells[:, [1, 2]] = cells[:, [2, 1]]
    return cells


def _correct_tetra_conns_writing(cells):
    cells[:, [2, 1]] = cells[:, [1, 2]]
    return cells


# uses meshio names
correct_cell_conns_reading = {'tetra': _correct_tetra_conns_reading}
correct_cell_conns_writing = {'tetra': _correct_tetra_conns_writing}


class HipMesh(Mesh):

    def __init__(self, points, cells, boundary, patches=None, point_data=None,
                 cell_data=None, field_data=None, point_sets=None, cell_sets=None,
                 gmsh_periodic=None, info=None):
        """
        Notes:
            Patches follow cells format.
        """
        super().__init__(points, cells, point_data=point_data,
                         cell_data=cell_data, field_data=field_data,
                         point_sets=point_sets, cell_sets=cell_sets,
                         gmsh_periodic=gmsh_periodic, info=info)
        self.boundary = boundary
        self.patches = patches


class Boundary:
    # for h5
    label_nodes = 'Boundary/bnode->node'
    label_groups = 'Boundary/bnode_lidx'

    def __init__(self, nodes, group_dims):
        # TODO: add patch labels? (they have to be handled differently)
        self.nodes = nodes
        self.group_dims = group_dims

    @ classmethod
    def read_from_h5(cls, h5_file):
        nodes = cls._read_dataset(h5_file, cls.label_nodes) - 1
        group_dims = cls._read_dataset(h5_file, cls.label_groups) - 1

        return Boundary(nodes, group_dims)

    @ staticmethod
    def _read_dataset(h5_file, label):
        return h5_file[label][()]

    def write_to_h5(self, h5_file):
        create_h5_dataset(h5_file, self.label_nodes, self.nodes + 1)
        create_h5_dataset(h5_file, self.label_groups, self.group_dims + 1)


def create_mesh_from_patches(mesh, ravel_cells=True):
    cells = mesh.patches

    all_req_dofs = []
    for cell in cells:
        all_req_dofs.extend(cell.data.ravel().tolist())
    all_req_dofs = set(all_req_dofs)

    dof_map = {dof: new_dof for new_dof, dof in enumerate(all_req_dofs)}

    new_cells = []
    for cell in cells:
        shape = cell.data.shape
        data = np.empty_like(cell.data)
        for i in range(shape[0]):
            for j in range(shape[1]):
                data[i, j] = dof_map[cell.data[i, j]]

        new_cells.append(CellBlock(cell.type, data))

    new_points = mesh.points[list(all_req_dofs), :]

    if ravel_cells:
        # this is required only due to way geo reading is done in tiny-3d-engine
        # assumes all the cells have same type
        data = new_cells[0].data
        for cells in new_cells[1:]:
            data = np.r_[data, cells.data]

    return Mesh(new_points, [CellBlock(new_cells[0].type, data)])
