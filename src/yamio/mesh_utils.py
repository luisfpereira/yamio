import numpy as np

import meshio

# TODO: from cell to cell_block (for readability)


def get_brep(points, cells):
    """Get boundary representation (brep).

    Notes:
        Boundary representations are edges (2d) or faces (3d).

        New connectivity numbers will be used (after removal of non-used points).
    """
    # TODO: make it scalable
    map_to_elem = {'triangle': from_triangle_to_line,
                   'quad': from_quad_to_line,
                   'hexahedron': from_hexa_to_quad}

    # name face is for simplification (represents edge if 2d)
    brep_cells = []
    for cell in cells:
        elem_type, faces = map_to_elem[cell.type](cell.data, keep_repeated=True)
        bnd_faces = np.array([face for face in faces if not is_repeated_conn(faces, face)])
        brep_cells.append(meshio.CellBlock(elem_type, bnd_faces))

    points, cells = get_local_points_and_cells(points, brep_cells)

    return points, cells


def from_hexa_to_quad(conns, keep_repeated=True):
    bottom_face = conns[:, :4]
    top_face = conns[:, 4:]
    front_face = conns[:, [1, 2, 6, 5]]
    back_face = conns[:, [0, 3, 7, 4]]
    right_face = conns[:, [2, 3, 7, 6]]
    left_face = conns[:, [1, 0, 4, 5]]

    new_conns = np.r_[bottom_face, top_face, front_face,
                      back_face, right_face, left_face]

    if not keep_repeated:
        new_conns = remove_repeated_conns(new_conns)

    return 'quad', new_conns


def from_quad_to_line(conns, keep_repeated=True):
    """
    Example:
        [0, 1, 2, 3] -> [0, 1], [1, 2], [2, 3], [3, 0]
    """
    line_conns = [conns[:, [i, i + 1]] for i in range(3)]
    line_conns.append(conns[:, [-1, 0]])

    new_conns = np.r_[line_conns].reshape(-1, 2)

    if not keep_repeated:
        new_conns = remove_repeated_conns(new_conns)

    return 'line', new_conns


def from_triangle_to_line(conns, keep_repeated=True):
    line_conns = [conns[:, [i, i + 1]] for i in range(2)]
    line_conns.append(conns[:, [-1, 0]])

    new_conns = np.r_[line_conns].reshape(-1, 2)

    if not keep_repeated:
        new_conns = remove_repeated_conns(new_conns)

    return 'line', new_conns


def from_tetra_to_tri(conns):
    # TODO: develop
    pass


def remove_repeated_conns(conns):
    """Removes repeated connectivities.

    Notes:
        Order of nodes in the connectivity does not matter.
    """
    new_conns = []
    for conn in conns:
        if not is_repeated_conn(new_conns, conn):
            new_conns.append(conn)

    return np.array(new_conns)


def is_repeated_conn(conns, conn, threshold=1):
    conn_cmp_set = set(conn.tolist())
    k = 0
    for conn in conns:
        # ???: is this line scalable? (alternative: reorder conns and set)
        if all([elem in conn_cmp_set for elem in conn]):
            k += 1
            if k > threshold:
                return True

    return False


def get_local_points_and_cells(points, cells):
    """Removes unused points and update dofs to start at 0.

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
