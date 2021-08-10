"""Reads and writes Cerfacs' XDMF files by wrapping meshio.

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
"""

# TODO: validation should be done with tests!
# TODO: add test to verify if passed mesh is not modified


from xml.etree import ElementTree as ET

import numpy as np
import h5py

import meshio
from meshio._common import num_nodes_per_cell
from meshio.xdmf.main import XdmfReader
from meshio.xdmf.common import xdmf_to_meshio_type
from meshio.xdmf.common import meshio_to_xdmf_type

from yamio.hip.xdmf2_utils import create_root
from yamio.hip.xdmf2_utils import create_topology_section
from yamio.hip.xdmf2_utils import create_geometry_section
from yamio.hip.xdmf2_utils import create_h5_dataset
from yamio.mesh_utils import get_local_points_and_cells


# TODO: deep changes in design (probably no need of a HipMesh -> explore meshio)


class HipReader(XdmfReader):
    # TODO: remove dependency in XDMFReader?

    def __init__(self):
        pass
        # self.filename = filename
        # self.h5_filename = h5_filename
        # if h5_filename is None:
        #     self.h5_filename = f"{'.'.join(filename.split('.')[:-1])}.h5"

    def _get_etree(self, filename):
        return ET.parse(filename, ET.XMLParser())

    def _get_topology(self, topology_elem):

        topology_type = xdmf_to_meshio_type[topology_elem.get("Type")]
        n_nodes_cell = num_nodes_per_cell[topology_type]

        data_item = list(list(topology_elem)[0])[0]

        data = self._read_data_item(data_item).reshape(-1, n_nodes_cell)

        return self._get_corrected_cells(data, topology_type)

    def _get_patch_topology(self, grid_elem):
        """
        Notes:
            h5's Patch contains local coordinates. Yet, by reading this
            information in h5's Boundary, we collect global information.
        """
        grid_name = grid_elem.get('Name')

        topology_elem = grid_elem.find('.//Topology')

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

        return grid_name, self._get_corrected_cells(data, topology_type)

    def _get_corrected_cells(self, data, topology_type):

        data = correct_cell_conns_reading.get(topology_type, lambda x: x)(data)
        data -= 1  # correct initial index
        cells = [meshio.CellBlock(topology_type, data)]

        return cells

    def _get_geometry(self, geometry_elem):
        return np.array([self._read_data_item(data_item) for data_item in list(geometry_elem)]).T

    def _get_bnd_patches_from_xdmf(self, tree):
        grid_elems = tree.findall('.//Grid')
        patches = [self._get_patch_topology(grid_elem) for grid_elem in grid_elems[1:]]

        return {patch_info[0]: patch_info[1][0] for patch_info in patches}

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

        bnd_patches = self._get_bnd_patches_from_xdmf(tree)
        # TODO: 2d patches should be read from h5 (and elem_type is line)

        return HipMesh(points, cells, bnd_patches=bnd_patches)


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
            # TODO: check if hip is able to read 2d mesh (with explicit patches)
            if len(mesh.bnd_patches) == 0:
                h5_file.create_group('Boundary')
            else:
                # TODO: write also xdmf? requires to write for bnd_quad also
                self._write_bnd_to_h5(h5_file, mesh.bnd_patches)

        # dump tree
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        tree.write(f'{file_basename}.mesh.xmf', xml_declaration=True,
                   encoding='utf-8')

        return tree

    def _write_topology(self, file, mesh, grid_elem):
        # ignores mixed case
        topology_type = mesh.cells[0].type
        data = mesh.cells[0].data.copy()
        data = correct_cell_conns_writing.get(topology_type, lambda x: x)(data)
        data += 1
        return create_topology_section(grid_elem, data, file,
                                       meshio_to_xdmf_type[topology_type][0],
                                       Format=self.fmt)

    def _write_geometry(self, file, mesh, grid_elem):
        return create_geometry_section(grid_elem, mesh.points, file,
                                       Format=self.fmt)

    def _write_bnd_to_h5(self, h5_file, bnd_patches):
        """
        Notes:
            Only writes to Boundary and let's hip take care of everything else.
        """

        # collect info
        patch_labels = [np.string_(name) for name in bnd_patches.keys()]
        bnd_node_groups = [np.unique(patch_nodes.data.ravel()) for patch_nodes in bnd_patches.values()]
        nodes = np.concatenate(bnd_node_groups, axis=0)
        group_dims = np.cumsum([len(node_groups) for node_groups in bnd_node_groups],
                               dtype=int)

        # write to h5
        create_h5_dataset(h5_file, 'Boundary/PatchLabels', patch_labels)
        create_h5_dataset(h5_file, 'Boundary/bnode->node', nodes + 1)
        create_h5_dataset(h5_file, 'Boundary/bnode_lidx', group_dims)


def _correct_tetra_conns_reading(cells):
    new_cells = cells.copy()
    new_cells[:, [1, 2]] = new_cells[:, [2, 1]]
    return new_cells


def _correct_tetra_conns_writing(cells):
    new_cells = cells.copy()
    new_cells[:, [2, 1]] = new_cells[:, [1, 2]]
    return new_cells


# uses meshio names
correct_cell_conns_reading = {'tetra': _correct_tetra_conns_reading}
correct_cell_conns_writing = {'tetra': _correct_tetra_conns_writing}


class HipMesh(meshio.Mesh):
    """
    Notes:
        I haven't found a simple way to use any of `meshio` inputs to handle
        boundary and patch data (that's the reason for this object).

        Patches follow cells format, but are a dict instead of list.
    """

    def __init__(self, points, cells, bnd_patches=None, point_data=None,
                 cell_data=None, field_data=None, point_sets=None, cell_sets=None,
                 gmsh_periodic=None, info=None):

        super().__init__(points, cells, point_data=point_data,
                         cell_data=cell_data, field_data=field_data,
                         point_sets=point_sets, cell_sets=cell_sets,
                         gmsh_periodic=gmsh_periodic, info=info)
        self.bnd_patches = bnd_patches


def create_mesh_from_patches(mesh, ravel_cells=True):
    # TODO: review (can be done better now)

    new_points, new_cells = get_local_points_and_cells(mesh.points, mesh.patches)

    if ravel_cells:
        # this is required only due to way geo reading is done in tiny-3d-engine
        # assumes all the cells have same type
        data = new_cells[0].data
        for cells in new_cells[1:]:
            data = np.r_[data, cells.data]

    return meshio.Mesh(new_points, [meshio.CellBlock(new_cells[0].type, data)])