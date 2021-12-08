
import numpy as np
import meshio
import h5py


def write(filename, mesh):
    """Extends XDMF writer to also create mesh with boundary patches.

    Notes:
        Still experimental. It will be extended to create an unique h5 file.
    """

    mesh.write(filename, file_format='xdmf')  # replicateds normal behavior

    if hasattr(mesh, 'bnd_patches') and mesh.bnd_patches:
        base_filename = '.'.join(filename.split('.')[:-1])
        bnd_filename = f'{base_filename}_bnd.xdmf'
        bnd_mesh = get_bnd_mesh(mesh)
        bnd_mesh.write(bnd_filename, file_format='xdmf')

        # write patch labels
        patch_labels = list(mesh.bnd_patches.keys())
        h5_filename = f'{base_filename}_bnd.h5'
        with h5py.File(h5_filename, 'r+') as h5_file:

            h5_file.create_dataset('PatchLabels', data=patch_labels,
                                   dtype='S24')


def get_bnd_mesh(mesh):
    bnd_cells = _get_merged_bnd_cells(mesh)
    patch_numbering_array = _get_bnd_patch_numbering(mesh)

    bnd_mesh = meshio.Mesh(mesh.points, cells=bnd_cells,
                           cell_data={'bnd_patches': [patch_numbering_array]})

    return bnd_mesh


def _get_merged_bnd_cells(mesh):
    # do not handle (on purpose) hybrid meshes
    cell_data = []
    elem_type = None
    for patch_cells in mesh.bnd_patches.values():
        if elem_type is None:
            elem_type = patch_cells.type

        if elem_type != patch_cells.type:
            raise Exception('Hybrid meshes are not supported')

        cell_data.extend(patch_cells.data.tolist())

    return [meshio.CellBlock(elem_type, np.array(cell_data))]


def _get_bnd_patch_numbering(mesh):
    # do not handle (on purpose) hybrid meshes
    # patch numbers follow bnd_patches order

    cell_data = []
    k = -1
    elem_type = None
    for patch_cells in mesh.bnd_patches.values():
        if elem_type is None:
            elem_type = patch_cells.type

        if elem_type != patch_cells.type:
            raise Exception('Hybrid meshes are not supported')

        k += 1
        cell_data.extend([k] * patch_cells.data.shape[0])

    return np.array(cell_data)
