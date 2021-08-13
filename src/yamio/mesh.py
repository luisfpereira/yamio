
import numpy as np
import meshio


class Mesh(meshio.Mesh):
    """See base class.

    Args:
        bnd_patches (dict) : Boundary patches.
            Follow cells format, but are a dict instead of list. May also
            contain a `np.array` with nodes, instead of `meshio.CellBlock`.

    Notes:
        I haven't found a simple way to use any of `meshio` inputs to handle
        boundary and patch data (that's the reason for this object).
    """

    def __init__(self, points, cells, bnd_patches=None, **kwargs):

        super().__init__(points, cells, **kwargs)
        self.bnd_patches = bnd_patches if bnd_patches is not None else {}

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

    def __eq__(self, other):
        # only points, cells and bnd_patches are verified

        # verify points
        if not np.allclose(self.points, other.points):
            return False

        # verify cells (assumes same order of cells blocks)
        for cells, other_cells in zip(self.cells, other.cells):
            if cells.type != other_cells.type:
                return False

            if not np.array_equal(cells.data, other_cells.data):
                return False

        # verify bnd_patches
        self_keys = set(self.bnd_patches.keys())
        other_keys = set(other.bnd_patches.keys())
        if self_keys != other_keys:
            return False

        for key in self_keys:
            self_patch = self.bnd_patches[key]
            other_patch = other.bnd_patches[key]
            if type(self_patch) != type(other_patch):
                return False

            if isinstance(self_patch, meshio.CellBlock):
                if not np.array_equal(self_patch.data, other_patch.data):
                    return False
            else:
                if not np.array_equal(self_patch, other_patch):
                    return False

        return True
