# Copyright 2022 The KerasCV Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import tensorflow as tf


class Equalize(tf.keras.layers.Layer):
    """Equalize performs histogram equalization on a channel-wise basis."""

    def __init__(self, rate=1.0, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def scale_channel(image, c):
        image = tf.cast(image[..., c], tf.int32)
        # Compute the histogram of the image channel.
        histo = tf.histogram_fixed_width(image, [0, 255], nbins=256)

        # For the purposes of computing the step, filter out the nonzeros.
        nonzero = tf.where(tf.not_equal(histo, 0))
        nonzero_histo = tf.reshape(tf.gather(histo, nonzero), [-1])
        step = (tf.reduce_sum(nonzero_histo) - nonzero_histo[-1]) // 255

        def build_mapping(histo, step):
            # Compute the cumulative sum, shifting by step // 2
            # and then normalization by step.
            lut = (tf.cumsum(histo) + (step // 2)) // step
            # Shift lut, prepending with 0.
            lut = tf.concat([[0], lut[:-1]], 0)
            # Clip the counts to be in range.  This is done
            # in the C code for image.point.
            return tf.clip_by_value(lut, 0, 255)

        # If step is zero, return the original image.  Otherwise, build
        # lut from the full histogram and step and then index from it.
        result = tf.cond(
            tf.equal(step, 0),
            lambda: image,
            lambda: tf.gather(build_mapping(histo, step), image),
        )

        return tf.cast(result, tf.uint8)

    def call(self, images):
        """call method for Equalize

        Args:
            images: Tensor of type int, pixels in range [0, 255], in RGB format.
        """
        # Assumes RGB for now.  Scales each channel independently
        # and then stacks the result.
        r = tf.map_fn(lambda x: Equalize.scale_channel(x, 0), images)
        g = tf.map_fn(lambda x: Equalize.scale_channel(x, 1), images)
        b = tf.map_fn(lambda x: Equalize.scale_channel(x, 2), images)
        images = tf.stack([r, g, b], -1)
        return images
