import math
import numpy as np
import tensorflow as tf

def radians(deg):
    return (math.pi / 180.0) * deg

def normalize(v):
    """

    NOTE: torch.norm() uses Frobineus norm which is Euclidean and L2
    """
    return v / tf.norm(v)

def gen_look_at_matrix(pos, look, up):
    """
    NOTE: torch version returned the contiguous tensor. Which is basically a hard
    copy of the transposed tensor. Without contiguous it's pointing to the same 
    tensor as the argument. In Tensorflow, it returns a copy(?)
    """
    d = normalize(look - pos)
    right = normalize(tf.linalg.cross(d, normalize(up)))
    new_up = normalize(tf.linalg.cross(right, d))
    z = tf.zeros([1], dtype=tf.float32)
    o = tf.ones([1], dtype=tf.float32)
    return tf.transpose(tf.stack([tf.concat([right , z], 0),
                                        tf.concat([new_up, z], 0),
                                        tf.concat([d     , z], 0),
                                        tf.concat([pos   , o], 0)]), 0, 1)

def gen_scale_matrix(scale):
    o = tf.ones([1], dtype=tf.float32)
    return tf.diag(tf.concat([scale, o], 0))

def gen_translate_matrix(translate):
    z = tf.zeros([1], dtype=tf.float32)
    o = tf.ones([1], dtype=tf.float32)
    return tf.stack([tf.concat([o, z, z, translate[0:1]], 0),
                        tf.concat([z, o, z, translate[1:2]], 0),
                        tf.concat([z, z, o, translate[2:3]], 0),
                        tf.concat([z, z, z, o], 0)])

def gen_perspective_matrix(fov, clip_near, clip_far):
    clip_dist = clip_far - clip_near
    cot = 1 / tf.tan(radians(fov / 2.0))
    z = tf.zeros([1], dtype=tf.float32)
    o = tf.ones([1], dtype=tf.float32)
    return tf.stack([tf.concat([cot,   z,             z,                       z], 0),
                        tf.concat([  z, cot,             z,                       z], 0),
                        tf.concat([  z,   z, 1 / clip_dist, - clip_near / clip_dist], 0),
                        tf.concat([  z,   z,             o,                       z], 0)])

def gen_rotate_matrix(angles):
    theta = angles[0]
    phi = angles[1]
    psi = angles[2]
    rot_x = tf.zeros((3, 3), dtype=tf.float32)
    rot_y = tf.zeros((3, 3), dtype=tf.float32)
    rot_z = tf.zeros((3, 3), dtype=tf.float32)
    rot_x[0, 0] = 1
    rot_x[0, 1] = 0
    rot_x[0, 2] = 0
    rot_x[1, 0] = 0
    rot_x[1, 1] = theta.cos()
    rot_x[1, 2] = theta.sin()
    rot_x[2, 0] = 0
    rot_x[2, 1] = -theta.sin()
    rot_x[2, 2] = theta.cos()
    
    rot_y[0, 0] = phi.cos()
    rot_y[0, 1] = 0
    rot_y[0, 2] = -phi.sin()
    rot_y[1, 0] = 0
    rot_y[1, 1] = 1
    rot_y[1, 2] = 0
    rot_y[2, 0] = phi.sin()
    rot_y[2, 1] = 0
    rot_y[2, 2] = phi.cos()
    
    rot_z[0, 0] = psi.cos()
    rot_z[0, 1] = -psi.sin()
    rot_z[0, 2] = 0
    rot_z[1, 0] = psi.sin()
    rot_z[1, 1] = psi.cos()
    rot_z[1, 2] = 0
    rot_z[2, 0] = 0
    rot_z[2, 1] = 0
    rot_z[2, 2] = 1
    return rot_z @ (rot_y @ rot_x)
