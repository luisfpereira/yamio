import xml.etree.cElementTree as etree

import meshio
import numpy as np
import h5py


meshio_to_dolfin_type = {"triangle": "triangle",
                         "tetra": "tetrahedron"}
dolfin_to_meshio_type = {item: key for key, item in meshio_to_dolfin_type.items()}


class DolfinSolReader:

    def read(self, sol_filename):
        h5_filename = '.'.join(sol_filename.split('.')[:-1]) + '.h5'
        tree = self._get_tree(sol_filename)
        is_time_series = self._is_time_series(tree)

        grid = tree.find('.//Grid')
        with h5py.File(h5_filename, 'r') as h5_file:
            if is_time_series:
                return self._read_time_series(grid, h5_file)
            else:
                return self._read_no_time(grid, h5_file)

    def _read_no_time(self, grid, h5_file):
        points, cells, point_sets, cell_sets, _ = self._read_frame(
            grid, h5_file, read_time=False)

        return meshio.Mesh(points, cells, point_sets=point_sets,
                           cell_sets=cell_sets)

    def _read_time_series(self, grid, h5_file):

        frame_grids = grid.findall('.//Grid')
        if len(frame_grids) == 1:  # assumes "virtual" time
            return self._read_no_time(frame_grids[0], h5_file)
        else:
            shared_mesh = self._shares_mesh(grid)
            if shared_mesh:
                return self._read_time_series_shared(frame_grids, h5_file)
            else:
                return self._read_time_series_no_shared(frame_grids, h5_file)

    def _read_time_series_shared(self, frame_grids, h5_file):

        def update_data(data, new_data):
            for key, value in new_data.items():
                data[key].append(value)

        # get first frame with mesh
        points, cells, point_sets_, cell_sets_, time = self._read_frame(
            frame_grids[0], h5_file)
        times = [time]

        # modify data
        point_sets = {}
        cell_sets = {}
        for key, value in point_sets_.items():
            point_sets[key] = [value]
        for key, value in cell_sets_.items():
            cell_sets[key] = [value]

        # get other data
        for frame_grid in frame_grids[1:]:
            _, _, point_sets_, cell_sets_, time = self._read_frame(
                frame_grid, h5_file, read_mesh=False)

            update_data(point_sets, point_sets_)
            update_data(cell_sets, cell_sets_)
            times.append(time)

        # create mesh
        return meshio.Mesh(points, cells, point_sets=point_sets,
                           cell_sets=cell_sets, info={'time': np.array(times)})

    def _read_time_series_no_shared(self, frame_grids, h5_file):
        meshes = []
        for frame_grid in frame_grids:
            points, cells, point_sets, cell_sets, time = self._read_frame(
                frame_grid, h5_file)

            meshes.append(meshio.Mesh(points, cells, point_sets=point_sets,
                                      cell_sets=cell_sets, info={'time': time}))

        return meshes

    def _read_frame(self, frame_grid, h5_file, read_mesh=True, read_time=True):
        points, cells, time = None, None, None

        if read_mesh:
            points, cells = self._read_mesh(frame_grid, h5_file)

        point_sets, cell_sets = self._read_grid_data(frame_grid, h5_file)

        if read_time:
            time = self._get_time(frame_grid)

        return points, cells, point_sets, cell_sets, time

    def _get_tree(self, sol_filename):
        with open(sol_filename, 'r') as file:
            tree = etree.parse(file)

        return tree

    def _get_time(self, grid):
        return float(grid.find('.//Time').get('Value'))

    def _read_mesh(self, grid, h5_file):

        # get info in xdmf
        topology_node = grid.find('.//Topology')
        topology_path = topology_node.find('.//DataItem').text.split(':')[-1]
        geometry_path = grid.find('.//Geometry').find('.//DataItem').text.split(':')[-1]

        # get elem_type, points and conns
        elem_type = topology_node.get('TopologyType').lower()
        conns = h5_file[topology_path][()]
        points = h5_file[geometry_path][()]

        # create cells
        cells = [meshio.CellBlock(dolfin_to_meshio_type[elem_type], conns)]

        return points, cells

    def _read_grid_data(self, grid, h5_file):
        point_sets = {}
        cell_sets = {}
        for attr in grid.findall('.//Attribute'):
            var_name = attr.get('Name')
            center = attr.get('Center')
            data_path = attr.find('.//DataItem').text.split(':')[-1]
            data = h5_file[data_path][()]

            if center == 'Node':
                point_sets[var_name] = data
            else:
                cell_sets[var_name] = data

        return point_sets, cell_sets

    def _is_time_series(self, tree):
        grid = tree.find('.//Grid')
        grid_name = grid.get('Name')

        return 'TimeSeries' in grid_name

    def _shares_mesh(self, node):
        return node.find('.//{http://www.w3.org/2001/XInclude}include') is not None
