"""Reads and writes Cerfacs' XDMF files.
"""

import os
import warnings

import numpy as np
import h5py

import meshio
from meshio._common import num_nodes_per_cell

from pyhip.commands.readers import read_hdf5_mesh
from pyhip.commands.writers import write_hdf5
from pyhip.commands.operations import hip_exit
from pyhip.commands.mesh_idcard import extract_hdf_meshinfo
from pyhip.hipster import pyhip_cmd


AXIS_MAP = {0: 'x', 1: 'y', 2: 'z'}
meshio_to_hip_type = {'line': 'bi',
                      'triangle': 'tri',
                      'quad': 'qua',
                      'tetra': 'tet',
                      'hexahedron': 'hex',
                      }
hip_to_meshio_type = {item: key for key, item in meshio_to_hip_type.items()}


class HipReader:

    def read(self, h5_filename):

        with h5py.File(h5_filename, 'r') as h5_file:
            cells = self._get_cells(h5_file)
            points = self._get_points(h5_file)
            bnd_patches = self._get_bnd_patches(h5_file)

        return HipMesh(points, cells, bnd_patches=bnd_patches)

    def _get_cells(self, h5_file):
        conns_basename = 'Connectivity'
        conns_name = list(h5_file[conns_basename].keys())[0]

        elem_type = hip_to_meshio_type[conns_name.split('-')[0]]
        conns_path = f'{conns_basename}/{conns_name}'
        conns = self._read_conns(h5_file, conns_path, elem_type)

        return [meshio.CellBlock(elem_type, conns)]

    def _read_conns(self, h5_file, conns_path, elem_type):
        n_nodes_cell = num_nodes_per_cell[elem_type]
        conns = h5_file[conns_path][()].reshape(-1, n_nodes_cell)
        return self._get_corrected_conns(conns, elem_type)

    def _get_points(self, h5_file):
        coords_basename = 'Coordinates'
        axes = list(h5_file[coords_basename].keys())
        return np.array([h5_file[f'{coords_basename}/{axis}'][()] for axis in axes]).T

    def _get_corrected_conns(self, conns, elem_type):
        conns = correct_cell_conns_reading.get(elem_type, lambda x: x)(conns)
        conns -= 1  # correct initial index

        return conns

    def _get_bnd_patches(self, h5_file):
        bnd_basename = 'Boundary'

        # get all conns
        for name in h5_file[bnd_basename].keys():
            if name.endswith('->node'):
                bnd_conns_name = name
                break
        else:
            return None

        hip_elem_type = bnd_conns_name.split('-')[0].split('_')[1]
        elem_type = hip_to_meshio_type[hip_elem_type]
        conns_path = f'{bnd_basename}/{bnd_conns_name}'
        conns = self._read_conns(h5_file, conns_path, elem_type)

        # get patch labels
        patch_labels = [name.decode('utf-8').strip() for name in h5_file[f'{bnd_basename}/PatchLabels'][()]]

        # organize patches
        last_indices = h5_file[f'{bnd_basename}/bnd_{hip_elem_type}_lidx'][()]
        fidx = 0
        bnd_patches = {}
        for patch_label, lidx in zip(patch_labels, last_indices):
            bnd_patches[patch_label] = meshio.CellBlock(elem_type, conns[fidx:lidx])
            fidx = lidx

        return bnd_patches


class HipWriter:

    def write(self, filename, mesh, commands=()):
        """
        Args:
            commands (array-like): Additional operations to be performed
                between reading and writing within `hip`.

        Notes:
            If patches do not exist, then the file can still be written, but
            several Hip features will not be available.
        """
        pre_read_commands = []
        file_basename = filename.split('.')[0]

        tmp_filename = f'{file_basename}_tmp.mesh.h5'
        with h5py.File(tmp_filename, 'w') as h5_file:

            # write mesh topology (conns)
            self._write_conns(h5_file, mesh)

            # write mesh coordinates
            self._write_coords(h5_file, mesh)

            # write boundary data (only in h5 file)
            if not hasattr(mesh, 'bnd_patches') or mesh.bnd_patches is None:
                h5_file.create_group('Boundary')
                pre_read_commands.append('set check 0')
            else:
                self._write_bnd_patches(h5_file, mesh.bnd_patches)

        # use pyhip to complete the file
        for command in pre_read_commands:
            pyhip_cmd(command)
        read_hdf5_mesh(tmp_filename)
        for command in commands:
            pyhip_cmd(command)
        write_hdf5(file_basename)
        hip_exit()

        # delete tmp file
        os.remove(tmp_filename)

        # validate mesh (volume)
        # TODO: remove when new version of hip is available
        try:
            mesh_filename = f'{file_basename}.mesh.h5'
            mesh_info, *_ = extract_hdf_meshinfo(mesh_filename)
            if mesh_info['Metric']['Element volume [m3]'].min < 0:
                raise Exception('Invalid grid: elements with negative volume')
        except KeyError:
            warnings.warn("Mesh validation was not performed.")

    def _write_conns(self, h5_file, mesh):
        # ignores mixed case
        elem_type = mesh.cells[0].type
        conns = mesh.cells[0].data.copy()
        conns = correct_cell_conns_writing.get(elem_type, lambda x: x)(conns)
        conns += 1

        hip_elem_type = meshio_to_hip_type[elem_type]
        h5_path = f'/Connectivity/{hip_elem_type}->node'
        h5_file.create_dataset(h5_path, data=conns.ravel())

    def _write_coords(self, h5_file, mesh):
        points = mesh.points
        for axis in range(points.shape[1]):
            h5_file.create_dataset(f'/Coordinates/{AXIS_MAP[axis]}',
                                   data=points[:, axis])

    def _write_bnd_patches(self, h5_file, bnd_patches):
        """
        Notes:
            Only writes to Boundary and let's hip take care of everything else.
        """

        # collect info
        patch_labels = list(bnd_patches.keys())
        bnd_node_groups = []
        for patch_nodes in bnd_patches.values():
            if isinstance(patch_nodes, meshio.CellBlock):
                bnd_node_groups.append(np.unique(patch_nodes.data.ravel()))
            else:
                bnd_node_groups.append(patch_nodes)

        nodes = np.concatenate(bnd_node_groups, axis=0)
        group_dims = np.cumsum([len(node_groups) for node_groups in bnd_node_groups],
                               dtype=int)

        # write to h5
        h5_file.create_dataset('Boundary/PatchLabels', data=patch_labels,
                               dtype='S24')
        h5_file.create_dataset('Boundary/bnode->node', data=nodes + 1)
        h5_file.create_dataset('Boundary/bnode_lidx', data=group_dims)


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
    # TODO: update mesh representation

    """See base class.

    Args:
        bnd_patches (dict) : Boundary patches.
            Follow cells format, but are a dict instead of list. May also
            contain a `np.array` with nodes, instead of `meshio.CellBlock`.

    Notes:
        I haven't found a simple way to use any of `meshio` inputs to handle
        boundary and patch data (that's the reason for this object).
    """

    def __init__(self, points, cells, bnd_patches=None, point_data=None,
                 cell_data=None, field_data=None, point_sets=None,
                 cell_sets=None, gmsh_periodic=None, info=None):

        super().__init__(points, cells, point_data=point_data,
                         cell_data=cell_data, field_data=field_data,
                         point_sets=point_sets, cell_sets=cell_sets,
                         gmsh_periodic=gmsh_periodic, info=info)
        self.bnd_patches = bnd_patches

    def __repr__(self):
        lines = []
        repr_str = super().__repr__()

        if self.bnd_patches:
            lines.append("\n  Boundary patches:")
            for patch_name, patch_nodes in self.bnd_patches.items():
                size = len(patch_nodes)
                if isinstance(patch_nodes, meshio.CellBlock):
                    lines.append(f"    {patch_name} ({patch_nodes.type}): {size}")
                else:
                    lines.append(f"    {patch_name}: {size}")

        return repr_str + "\n".join(lines)
