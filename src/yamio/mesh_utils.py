import numpy as np

import meshio


def get_faces_from_conns(conns):
    map_to_elem = {8: from_hexa_to_quad}
    return map_to_elem[conns.shape[1]](conns)


def get_bnd_faces_from_conns(conns):
    elem_type, faces = get_faces_from_conns(conns)
    return elem_type, get_bnd_faces_from_faces(faces)


def from_hexa_to_quad(conns):
    bottom_face = conns[:, :4]
    top_face = conns[:, 4:]
    front_face = conns[:, [1, 2, 6, 5]]
    back_face = conns[:, [0, 3, 7, 4]]
    right_face = conns[:, [2, 3, 7, 6]]
    left_face = conns[:, [1, 0, 4, 5]]

    return 'quad', np.r_[bottom_face, top_face, front_face,
                         back_face, right_face, left_face]


def from_tetra_to_tri(conns):
    # TODO: develop
    pass


def get_bnd_faces_from_faces(faces):
    """Get boundary faces (i.e. faces that belong only to one element).
    """
    bnd_faces = []
    for face_cmp in faces:
        face_cmp_set = set(face_cmp.tolist())

        k = 0
        for face in faces:
            # TODO: is this line scalable?
            if all([elem in face_cmp_set for elem in face]):
                k += 1
                if k > 1:
                    break
        else:
            bnd_faces.append(face_cmp)

    return np.array(bnd_faces)


def get_local_points_and_cells(points, cells):
    """Removes unused dofs and update dofs to start at 0.

    Notes:
        Used to build a mesh with a subset of initial cells.
    """

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

        new_cells.append(meshio.CellBlock(cell.type, data))

    new_points = points[list(all_req_dofs), :]

    return new_points, new_cells
