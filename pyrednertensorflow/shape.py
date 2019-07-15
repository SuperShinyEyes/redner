from typing import List, Set, Dict, Tuple, Optional, Callable, Union
import pyrednertensorflow as pyredner
import tensorflow as tf
import math
import numpy as np
import pdb

def compute_vertex_normal(vertices, indices):
    def dot(v1, v2):
        return tf.math.reduce_sum(v1 * v2, axis=1)
    def squared_length(v):
        return tf.math.reduce_sum(v * v, axis=1)
    def length(v):
        return tf.sqrt(squared_length(v))
    # Nelson Max, "Weights for Computing Vertex Normals from Facet Vectors", 1999
    normals = tf.constant(np.zeros(vertices.shape, dtype = np.float32))

    # NOTE: Try tf.TensorArray()
    v = [
        tf.gather(vertices, indices[:,0]),
        tf.gather(vertices, indices[:,1]),
        tf.gather(vertices, indices[:,2])
    ]
    # v = [vertices[indices[:, 0], :],
    #      vertices[indices[:, 1], :],
    #      vertices[indices[:, 2], :]]

    contribs = []
    for i in range(3):
        v0 = v[i]
        v1 = v[(i + 1) % 3]
        v2 = v[(i + 2) % 3]
        e1 = v1 - v0
        e2 = v2 - v0
        e1_len = length(e1)
        e2_len = length(e2)
        side_a = e1 / tf.reshape(e1_len, [-1, 1])
        side_b = e2 / tf.reshape(e2_len, [-1, 1])
        if i == 0:
            n = tf.linalg.cross(side_a, side_b)
            n = n / tf.reshape(length(n), [-1, 1])
        angle = tf.where(dot(side_a, side_b) < 0, 
            math.pi - 2.0 * tf.asin(0.5 * length(side_a + side_b)),
            2.0 * tf.asin(0.5 * length(side_b - side_a)))
        sin_angle = tf.sin(angle)
        
        # XXX: Inefficient but it's PyTorch's limitation
        contrib = tf.reshape((sin_angle / (e1_len * e2_len)), (-1, 1))
        contrib = n * tf.broadcast_to(contrib, [tf.shape(contrib)[0],3]) # In torch, `expand(-1, 3)`

        index = tf.reshape(indices[:, i],(-1, 1))
        index = tf.broadcast_to(index, [tf.shape(index)[0],3])     # In torch, `expand([-1, 3])`

        """
        FIXME: Tensorflow's `scatter_add` expects equal shapes.
        """
        normals = pyredner.scatter_add(
            normals,    # 6460 x 3
            index,      # 12152 x 3
            contrib     # 12152 x 3
        )
        
        contribs.append(contrib)

    normals = normals / tf.reshape(length(normals), [-1, 1])

    if pyredner.IS_UNIT_TEST:
        return normals, contribs, v
    return normals

class Shape:
    def __init__(self, 
                 vertices: tf.Tensor, 
                 indices: tf.Tensor, 
                 uvs: Optional[tf.Tensor] = None, 
                 normals: Optional[tf.Tensor] = None, 
                 material_id: int = 0):
        assert(vertices.dtype == tf.float32)
        assert(indices.dtype == tf.int32)
        if (uvs is not None):
            assert(uvs.dtype == tf.float32)
        if (normals is not None):
            assert(normals.dtype == tf.float32)
        # if pyredner.get_use_gpu():
        #     assert(uvs is None)
        #     assert(normals is None)
        # else:
        #     assert(uvs is None)
        #     assert(normals is None)

        self.vertices = vertices
        self.indices = indices
        self.uvs = uvs
        self.normals = normals
        self.material_id = material_id
        self.light_id = -1

    def state_dict(self):
        return {
            'vertices': self.vertices,
            'indices': self.indices,
            'uvs': self.uvs,
            'normals': self.normals,
            'material_id': self.material_id,
            'light_id': self.light_id,
        }

    @classmethod
    def load_state_dict(cls, state_dict):
        out = cls(
            state_dict['vertices'],
            state_dict['indices'],
            state_dict['uvs'],
            state_dict['normals'],
            state_dict['material_id'])
        return out