Yet another mesh I/O
====================

`yamio` aims to bridge [`meshio`](https://pypi.org/project/meshio/) and [`pyhip`](https://pypi.org/project/pyhip/).


Both projects support various formats for representing unstructured grids. Nevertheless, they were unable to communicate without loss of information. `yamio` extends `meshio` by adding treatment to boundary patches through extension of the `meshio.Mesh` object and by defining a direct writer to `pyhip` main format (`.mesh.xmf`). Additionally, `yamio` adds support for [Ensight's gold files](https://dav.lbl.gov/archive/NERSC/Software/ensight/doc/Manuals/UserManual.pdf).



Install with


```bash
pip install yamio
```


The basic usage is very similar to `meshio`. 

To read a mesh

```python
import yamio

mesh = yamio.read(filename)  # extension inferred
```

To write a mesh

```python
import yamio

mesh = yamio.write(filename, mesh)  # extension inferred
```


Additionally to `meshio`, the following formats are available: `.mesh.xmf` (`pyhip` main format) and `.geo`.

Note: after you have a `.mesh.xmf` mesh, you can rely on `pyhip` to do additional mesh conversions.
