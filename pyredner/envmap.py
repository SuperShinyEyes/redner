import pyredner
import tensorflow as tf
import math

class EnvironmentMap:
    def __init__(self, values, env_to_world = tf.eye(4, 4)):
        # Convert to constant texture if necessary
        if isinstance(values, tf.Tensor):
            values = pyredner.Texture(values)

        assert(values.texels.is_contiguous())
        assert(values.texels.dtype == tf.float32)
        if pyredner.get_use_gpu():
            assert(values.texels.is_cuda)
        else:
            assert(not values.texels.is_cuda)

        # Build sampling table
        luminance = 0.212671 * values.texels[:, :, 0] + \
                    0.715160 * values.texels[:, :, 1] + \
                    0.072169 * values.texels[:, :, 2]
        # For each y, compute CDF over x
        sample_cdf_xs_ = tf.cumsum(luminance, axis=1)
        y_weight = tf.sin(\
        	math.pi * (tf.range(luminance.shape[0],
                dtype = tf.float32, name='EnvironmentMap.y_weight') + 0.5) \
             / float(luminance.shape[0]))
        # Compute CDF for x
        sample_cdf_ys_ = tf.cumsum(sample_cdf_xs_[:, -1] * y_weight, axis=0)
        pdf_norm = (luminance.shape[0] * luminance.shape[1]) / \
        	(sample_cdf_ys_[-1].item() * (2 * math.pi * math.pi))
        # Normalize to [0, 1)
        sample_cdf_xs = (sample_cdf_xs_ - sample_cdf_xs_[:, 0:1]) / \
            tf.math.maximum(sample_cdf_xs_[:, (luminance.shape[1] - 1):luminance.shape[1]],
                1e-8 * tf.ones(
                    (sample_cdf_xs_.shape[0], 1)
                    )
                )
        sample_cdf_ys = (sample_cdf_ys_ - sample_cdf_ys_[0]) / \
            tf.math.maximum(sample_cdf_ys_[-1], tf.constant([1e-8]))

        self.values = values
        self.env_to_world = env_to_world
        self.world_to_env = tf.linalg.inv(env_to_world).contiguous()
        self.sample_cdf_ys = sample_cdf_ys.contiguous()
        self.sample_cdf_xs = sample_cdf_xs.contiguous()
        self.pdf_norm = pdf_norm

