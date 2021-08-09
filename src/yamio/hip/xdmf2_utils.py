import os

from xml.etree import ElementTree as ET

from meshio.xdmf.common import numpy_to_xdmf_dtype


# TODO: rethink design!


def get_namespace():
    return "http://www.w3.org/2003/XInclude"


def create_root(version='2.0', Format='HDF', **kwargs):
    root = ET.Element("Xdmf", Version=version,
                      attrib={'xmlns:xi': get_namespace()},
                      **kwargs)

    return root


def create_h5_dataset(file, name, data, **kwargs):
    '''
    Args:
        **kwargs: e.g. compression
    '''
    file.create_dataset(name, data=data, **kwargs)


def create_topology_section(parent, data, h5_file, topology_type, Format='HDF'):
    topology = create_topology_item(parent, topology_type, data.shape[0])
    topology_function = create_topology_function(topology, data.size)
    create_topology_data_item(topology_function, data, h5_file, topology_type,
                              Format=Format)

    return topology


def create_topology_item(parent, Type, NumberOfElements, **kwargs):
    kwargs.update({'Type': Type,
                   'NumberOfElements': str(NumberOfElements)})
    return _create_node(parent, 'Topology', **kwargs)


def create_topology_function(parent, Dimensions, Function="$0 - 1", **kwargs):

    kwargs.update({'Dimensions': str(Dimensions),
                   'Function': Function,
                   'ItemType': 'Function'})
    return _create_node(parent, 'DataItem', **kwargs)


def create_topology_data_item(parent, data, h5_file, elem_type, Format="HDF",
                              **kwargs):
    h5_store_path = f'/Connectivity/{elem_type[:3].lower()}->node'

    return _create_data_item(parent, data.ravel(), h5_file, h5_store_path, Format,
                             **kwargs)


def create_geometry_section(parent, data, h5_file, Format="HDF"):
    d = data.shape[1]
    geometry = create_geom_item(parent, d)
    for axis in range(d):
        create_geom_data_item(geometry, data[:, axis], h5_file, axis, Format)

    return geometry


def get_geometry_type(d):
    return 'X_Y_Z'[:2 * d + 1]


def create_geom_item(parent, d, **kwargs):
    geometry_type = get_geometry_type(d - 1)
    kwargs.update({'GeometryType': geometry_type})

    return _create_node(parent, 'Geometry', **kwargs)


def create_geom_data_item(parent, data, h5_file, axis, Format='HDF', **kwargs):
    # if need to h5_file args, then pass object with create_dataset method
    axis_map = {0: 'x', 1: 'y', 2: 'z'}
    h5_store_path = f'/Coordinates/{axis_map[axis]}'

    return _create_data_item(parent, data, h5_file, h5_store_path, Format,
                             **kwargs)


def _create_data_item(parent, data, h5_file, h5_store_path, Format='HDF',
                      **kwargs):
    # if need to h5_file args, then pass object with create_dataset method

    # get info from data
    dims = data.shape[0]
    data_type, _ = numpy_to_xdmf_dtype[data.dtype.name]

    # create xml
    kwargs.update({'Dimensions': str(dims),
                   'DataType': data_type,
                   'Format': Format})
    data_item = _create_node(parent, 'DataItem', **kwargs)

    create_h5_dataset(h5_file, h5_store_path, data)
    data_item.text = create_h5_text(os.path.basename(h5_file.filename), h5_store_path)

    return data_item


def create_h5_text(filename, hdf5_path):
    return f'{filename}:{hdf5_path}'


def _create_node(parent, name, **kwargs):
    return ET.SubElement(parent, name, **kwargs)
