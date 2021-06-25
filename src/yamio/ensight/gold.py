'''Reads and writes Ensight's gold casefile format.

Notes:
    Still a very naive implementation of a writer and a reader.

    Supports:

    Validated elements:
        * quad



References:
    [1] [EnSight User Manual](https://dav.lbl.gov/archive/NERSC/Software/ensight/doc/Manuals/UserManual.pdf)

'''

import numpy as np


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


# TODO: add simple reader?

class GeoWriter:

    def write(self, filename, mesh, description=None, node_id='off',
              element_id='off'):
        '''
        Args:
            description (array-like, shape=[2]): two initial lines of the file.
        '''
        # TODO: add extents
        if description is None:
            description = self._get_default_description()

        # headers
        text = description.copy()
        text.append(f'node id {node_id}')
        text.append(f'node_id {element_id}')

        # part
        text.extend(self._add_part(1, '', mesh.points, mesh.cells))

        # write file
        with open(filename, 'w') as file:
            file.write('\n'.join(self._process_text(text)))

    def _get_default_description(self):
        return ['`yamio` generated file', '']

    def _add_part(self, number, description, coords, cells):
        '''
        Notes:
            * x, y and z coordinates are mandatory, even if 2D.
            * Print order: all x-> all y -> all z.

        '''
        text = ['part', number]
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
        conns += 1
        text = [elem_type, n_elems]
        text.extend(conns.tolist())

        return text

    def _process_text(self, text):
        return [str(elem) if type(elem) is not list else ' '.join([str(e) for e in elem]) for elem in text]
