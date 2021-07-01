import numpy as np


def get_faces_from_conns(conns):
    map_to_elem = {8: from_hexa_to_quad}
    return map_to_elem[conns.shape[1]](conns)


def get_bnd_faces_from_conns(conns):
    faces = get_faces_from_conns(conns)
    return get_bnd_faces_from_faces(faces)


def from_hexa_to_quad(conns):
    bottom_face = conns[:, :4]
    top_face = conns[:, 4:]
    front_face = conns[:, [1, 2, 6, 5]]
    back_face = conns[:, [0, 3, 7, 4]]
    right_face = conns[:, [2, 3, 7, 6]]
    left_face = conns[:, [1, 0, 4, 5]]

    return np.r_[bottom_face, top_face, front_face,
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
