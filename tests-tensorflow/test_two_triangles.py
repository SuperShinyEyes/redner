import tensorflow as tf
tf.enable_eager_execution()
tfe = tf.contrib.eager
import pyrednertensorflow as pyredner
import numpy as np
import pdb

# Optimize six vertices of a two triangles

# Use GPU if available
pyredner.set_use_gpu(False)

# Set up the scene using Pytorch tensor
position = tfe.Variable([0.0, 0.0, -5.0], dtype=tf.float32)
look_at = tfe.Variable([0.0, 0.0, 0.0], dtype=tf.float32)
up = tfe.Variable([0.0, 1.0, 0.0], dtype=tf.float32)
fov = tfe.Variable([45.0], dtype=tf.float32)
clip_near = 1e-2

resolution = (256, 256)
cam = pyredner.Camera(position = position,
                      look_at = look_at,
                      up = up,
                      fov = fov,
                      clip_near = clip_near,
                      resolution = resolution)

mat_green = pyredner.Material(
    diffuse_reflectance = tfe.Variable([0.35, 0.75, 0.35],
    ))
mat_red = pyredner.Material(
    diffuse_reflectance = tfe.Variable([0.75, 0.35, 0.35],
    ))
mat_black = pyredner.Material(
    diffuse_reflectance = tfe.Variable([0.0, 0.0, 0.0],
    ))
materials = [mat_green,mat_red,mat_black]
tri0_vertices = tfe.Variable(
    [[-1.7,1.0,0.0], [1.0,1.0,0.0], [-0.5,-1.0,0.0]],
    )
tri1_vertices = tfe.Variable(
    [[-1.0,1.5,1.0], [0.2,1.5,1.0], [0.2,-1.5,1.0]],
    )
tri0_indices = tfe.Variable([[0, 1, 2]], dtype=tf.int32, )
tri1_indices = tfe.Variable([[0, 1, 2]], dtype=tf.int32, )
shape_tri0 = pyredner.Shape(tri0_vertices, tri0_indices, None, None, 0)
shape_tri1 = pyredner.Shape(tri1_vertices, tri1_indices, None, None, 1)
light_vertices = tfe.Variable(
    [[-1.0,-1.0,-7.0],[1.0,-1.0,-7.0],[-1.0,1.0,-7.0],[1.0,1.0,-7.0]],
    )
light_indices = tfe.Variable([[0,1,2],[1,3,2]], dtype=tf.int32, )
shape_light = pyredner.Shape(light_vertices, light_indices, None, None, 2)
shapes = [shape_tri0, shape_tri1, shape_light]
light_intensity = tfe.Variable([20.0,20.0,20.0])
# The first argument is the shape id of the light
light = pyredner.AreaLight(2, light_intensity)
area_lights = [light]
scene = pyredner.Scene(cam, shapes, materials, area_lights)
scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 256,
    max_bounces = 1)

# Render our target
img = pyredner.render(0, *scene_args)
pyredner.imwrite(img, 'results/test_two_triangles/target.exr')
pyredner.imwrite(img, 'results/test_two_triangles/target.png')
target = pyredner.imread('results/test_two_triangles/target.exr')

# Perturb the scene, this is our initial guess
shape_tri0.vertices = tfe.Variable(
    [[-1.3,1.5,0.1], [1.5,0.7,-0.2], [-0.8,-1.1,0.2]],
    dtype=tf.float32,
    trainable=True)
shape_tri1.vertices = tfe.Variable(
    [[-0.5,1.2,1.2], [0.3,1.7,1.0], [0.5,-1.8,1.3]],
    dtype=tf.float32,
    trainable=True)
scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 256,
    max_bounces = 1)
# Render the initial guess
img = pyredner.render(1, *scene_args)
pyredner.imwrite(img, 'results/test_two_triangles/init.png')
diff = tf.abs(target - img)
pyredner.imwrite(diff, 'results/test_two_triangles/init_diff.png')

# Optimize for triangle vertices
optimizer = tf.train.AdamOptimizer(5e-2)
scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 4,
    max_bounces = 1)
for t in range(200):
    print('iteration:', t)
    
    # Forward pass: render the image
    with tf.GradientTape() as tape:
        img = pyredner.render(t+1, *scene_args)

        pyredner.imwrite(img, 'results/test_two_triangles/iter_{}.png'.format(t))
        loss = tf.reduce_sum(tf.square(img - target))
        print('loss:', loss)

    grads = tape.gradient(loss, [shape_tri0.vertices, shape_tri1.vertices])

    optimizer.apply_gradients(
        zip(grads, [shape_tri0.vertices, shape_tri1.vertices])
        )

    print('tri0:', shape_tri0.vertices)
    print('tri1:', shape_tri1.vertices)

scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 256,
    max_bounces = 1)
img = pyredner.render(202, *scene_args)
pyredner.imwrite(img, 'results/test_two_triangles/final.exr')
pyredner.imwrite(img, 'results/test_two_triangles/final.png')
pyredner.imwrite(tf.abs(target - img).cpu(), 'results/test_two_triangles/final_diff.png')

from subprocess import call
call(["ffmpeg", "-framerate", "24", "-i",
    "results/test_two_triangles/iter_%d.png", "-vb", "20M",
    "results/test_two_triangles/out.mp4"])