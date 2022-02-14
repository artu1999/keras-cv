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
    """Equalize performs histogram equalization on a channel-wise basis.

    Args:
        bins: number of bins to use in histogram equalization.

    Usage:
        ```
        equalize = Equalize()

        (images, labels), _ = tf.keras.data.cifar10.load_data()
        # Note that images are an int32 Tensor with values in the range [0, 255]
        images = equalize(images)
        ```

    Call arguments:
        images: Tensor of type int, pixels in range [0, 255], in RGB format.
    """

    def __init__(self, bins=256, **kwargs):
        super().__init__(**kwargs)
        self.bins = bins

    def equalize_channel(self, image, channel_index):
        """equalize_channel performs histogram equalization on a single channel.

        Args:
            image: int Tensor with pixels in range [0, 255], RGB format,
                with channels last
            channel_index: channel to equalize
        """
        dtype = image.dtype
        image = tf.cast(image[..., channel_index], tf.int32)
        # Compute the histogram of the image channel.
        histogram = tf.histogram_fixed_width(image, [0, 255], nbins=self.bins)

        # For the purposes of computing the step, filter out the nonzeros.
        nonzero = tf.where(tf.not_equal(histogram, 0))
        nonzero_histogram = tf.reshape(tf.gather(histogram, nonzero), [-1])
        step = (tf.reduce_sum(nonzero_histogram) - nonzero_histogram[-1]) // (
            self.bins - 1
        )

        def build_mapping(histogram, step):
            # Compute the cumulative sum, shifting by step // 2
            # and then normalization by step.
            lookup_table = (tf.cumsum(histogram) + (step // 2)) // step
            # Shift lookup_table, prepending with 0.
            lookup_table = tf.concat([[0], lookup_table[:-1]], 0)
            # Clip the counts to be in range.  This is done
            # in the C code for image.point.
            return tf.clip_by_value(lookup_table, 0, 255)

        # If step is zero, return the original image.  Otherwise, build
        # lookup table from the full histogram and step and then index from it.
        result = tf.cond(
            tf.equal(step, 0),
            lambda: image,
            lambda: tf.gather(build_mapping(histogram, step), image),
        )

        return tf.cast(result, dtype)

    def call(self, images):
        if not images.dtype.is_integer:
            raise ValueError(
                "Equalize.call(images) expects images to be a "
                "Tensor of type int, with values in range [0, 255]. "
                f"got images.dtype={images.dtype}."
            )

        # Assumes RGB for now.  Scales each channel independently
        # and then stacks the result.
        r = tf.map_fn(lambda x: self.equalize_channel(x, 0), images)
        g = tf.map_fn(lambda x: self.equalize_channel(x, 1), images)
        b = tf.map_fn(lambda x: self.equalize_channel(x, 2), images)
        # TODO(lukewood): ideally this should be vectorized.

        images = tf.stack([r, g, b], axis=-1)
        return images
