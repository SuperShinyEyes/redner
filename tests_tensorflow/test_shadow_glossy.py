import tensorflow as tf
tf.enable_eager_execution()
tfe = tf.contrib.eager
import numpy as np
import pyrednertensorflow as pyredner
import pdb

# Optimize four vertices of a shadow blocker, where the receiver is highly glossy

# Use GPU if available
pyredner.set_use_gpu(False)

# Set up the scene using Pytorch tensor
position = tfe.Variable([0.0, 2.0, -4.0])
look_at = tfe.Variable([0.0, -2.0, 0.0])
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

mat_shiny = pyredner.Material(
    diffuse_reflectance = tfe.Variable([0.0, 0.0, 0.0], dtype=tf.float32),
    specular_reflectance = tfe.Variable([1.0, 1.0, 1.0], dtype=tf.float32),
    roughness = tfe.Variable([0.0005], dtype=tf.float32))
mat_grey = pyredner.Material(
    diffuse_reflectance = tfe.Variable([0.5, 0.5, 0.5], dtype=tf.float32))
mat_black = pyredner.Material(
    diffuse_reflectance = tfe.Variable([0.0, 0.0, 0.0], dtype=tf.float32))
materials = [mat_shiny, mat_grey, mat_black]
# materials = [mat_grey, mat_black]

#############################################
# Shapes

# floor
floor_vertices = tfe.Variable(
    [[-4.0,0.0,-4.0],[-4.0,0.0,4.0],[4.0,0.0,-4.0],[4.0,0.0,4.0]],
    dtype=tf.float32
    )
floor_indices = tfe.Variable([[0,1,2], [1,3,2]], dtype=tf.int32)
shape_floor = pyredner.Shape(floor_vertices, floor_indices, None, None, 0)

# blocker
blocker_vertices = tfe.Variable(
    [[0.0,1.0,0.5],[0.0,3.0,0.5],[0.8,1.0,0.5],[0.8,3.0,0.5]],
    dtype=tf.float32
    )
blocker_indices = tfe.Variable([[0,1,2], [1,3,2]], dtype=tf.int32)
shape_blocker = pyredner.Shape(blocker_vertices, blocker_indices, None, None, 1)

# light
light_vertices = tfe.Variable(
    [[-2.0,0.0,4.0],[-2.0,12.0,4.0],[2.0,0.0,4.0],[2.0,12.0,4.0]], dtype=tf.float32
    )
light_indices = tfe.Variable([[0,1,2], [1,3,2]], dtype=tf.int32)
shape_light = pyredner.Shape(light_vertices, light_indices, None, None, 2)

shapes = [shape_floor, shape_blocker, shape_light]

###############################################
# Light
light_intensity = tfe.Variable([0.5, 0.5, 0.5], dtype=tf.float32)
# The first argument is the shape id of the light
light = pyredner.AreaLight(2, light_intensity)
area_lights = [light]

###############################################
# Scene
scene = pyredner.Scene(cam, shapes, materials, area_lights)

scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 1024,   # NOTE: Different from test_shadow_bocker's 256
    max_bounces = 1)

# Alias of the render function

# Render our target
img = pyredner.render(0, *scene_args)
pyredner.imwrite(img, 'results/test_shadow_glossy/target.exr')
pyredner.imwrite(img, 'results/test_shadow_glossy/target.png')
target = pyredner.imread('results/test_shadow_glossy/target.exr')

# Perturb the scene, this is our initial guess
shape_blocker.vertices = tfe.Variable(
    [[-0.6,0.9,0.4],[-0.8,3.3,0.7],[0.2,1.1,0.6],[0.3,3.2,0.4]],
    dtype=tf.float32,
    trainable=True)
scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 1024,    # NOTE: Different from test_shadow_bocker's 256
    max_bounces = 1)
# Render the initial guess
img = pyredner.render(1, *scene_args)
pyredner.imwrite(img, 'results/test_shadow_glossy/init.png')
diff = tf.abs(target - img)
pyredner.imwrite(diff, 'results/test_shadow_glossy/init_diff.png')

# Optimize for blocker vertices
# optimizer = torch.optim.Adam([shape_blocker.vertices], lr=5e-2)
optimizer = tf.train.AdamOptimizer(2e-2)
for t in range(200):
    print('iteration:', t)
    scene_args = pyredner.serialize_scene(
        scene = scene,
        num_samples = 4,
        max_bounces = 1)
    
    with tf.GradientTape() as tape:
        # Forward pass: render the image
        img = pyredner.render(t+1, *scene_args)
        pyredner.imwrite(img, 'results/test_shadow_glossy/iter_{}.png'.format(t))
        loss = tf.reduce_sum(tf.square(img - target))
    print('loss:', loss)

    grads = tape.gradient(loss, [shape_blocker.vertices])
    print('grad:', grads)

    optimizer.apply_gradients(
        zip(grads, [shape_blocker.vertices])
        )
    print('vertices:', shape_blocker.vertices)


scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 1024,
    max_bounces = 1)
img = pyredner.render(202, *scene_args)
pyredner.imwrite(img, 'results/test_shadow_glossy/final.exr')
pyredner.imwrite(img, 'results/test_shadow_glossy/final.png')
pyredner.imwrite(tf.abs(target - img).cpu(), 'results/test_shadow_glossy/final_diff.png')

from subprocess import call
call(["ffmpeg", "-framerate", "24", "-i",
    "results/test_shadow_glossy/iter_%d.png", "-vb", "20M",
    "results/test_shadow_glossy/out.mp4"])