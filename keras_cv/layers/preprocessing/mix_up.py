import tensorflow as tf
import tensorflow.keras as keras
import tensorflow.keras.layers as layers
from tensorflow.python.platform import tf_logging as logging


class MixUp(layers.Layer):
    """MixUp implements the MixUp data augmentation technique.

    Args:
        rate: Float between 0 and 1.  The fraction of samples to augment.
        alpha: Float between 0 and 1.  Inverse scale parameter for the gamma distribution.
            This controls the shape of the distribution from which the smoothing values are 
            sampled.  Defaults 0.2, which is a recommended value when training an imagenet1k
            classification model.
        label_smoothing: Float between 0 and 1.  The coefficient used in label smoothing.  Default 0.0.
    References:
        https://arxiv.org/abs/1710.09412.

    Sample usage:
    ```python
    (images, labels), _ = tf.keras.datasets.cifar10.load_data()
    mixup = keras_cv.layers.preprocessing.mix_up.MixUp(10)
    augmented_images, updated_labels = mixup(images, labels)
    ```
    """

    def __init__(
        self, rate, label_smoothing=0.0, alpha=0.2, seed=None, **kwargs
    ):
        super(MixUp, self).__init__(*kwargs)
        self.alpha = alpha
        self.rate = rate
        self.label_smoothing = label_smoothing
        self.seed = seed

    @staticmethod
    def _sample_from_beta(alpha, beta, shape):
        sample_alpha = tf.random.gamma(shape, 1.0, beta=alpha)
        sample_beta = tf.random.gamma(shape, 1.0, beta=beta)
        return sample_alpha / (sample_alpha + sample_beta)

    def call(self, images, labels):
        """call method for the MixUp layer.

        Args:
            images: Tensor representing images of shape [batch_size, width, height, channels], with dtype tf.float32.
            labels: One hot encoded tensor of labels for the images, with dtype tf.float32.
        Returns:
            images: augmented images, same shape as input.
            labels: updated labels with both label smoothing and the cutmix updates applied.
        """

        if tf.shape(images)[0] == 1:
            logging.warning(
                "MixUp received a single image to `call`.  The layer relies on combining multiple examples, "
                "and as such will not behave as expected.  Please call the layer with 2 or more samples."
            )

        augment_cond = tf.less(
            tf.random.uniform(shape=[], minval=0.0, maxval=1.0), self.rate
        )
        # pylint: disable=g-long-lambda
        mixup_augment = lambda: self._update_labels(*self._mixup(images, labels))
        no_augment = lambda: (images, self._smooth_labels(labels))
        return tf.cond(augment_cond, mixup_augment, no_augment)

    def _mixup(self, images, labels):
        batch_size = tf.shape(images)[0]
        permutation_order = tf.random.shuffle(tf.range(0, batch_size), seed=self.seed)

        lambda_sample = MixUp._sample_from_beta(self.alpha, self.alpha, (batch_size,))
        lambda_sample = tf.reshape(lambda_sample, [-1, 1, 1, 1])

        mixup_images = tf.gather(images, permutation_order)
        images = lambda_sample * images + (1.0 - lambda_sample) * mixup_images

        return images, labels, tf.squeeze(lambda_sample), permutation_order

    def _update_labels(self, images, labels, lambda_sample, permutation_order):
        labels_smoothed = self._smooth_labels(labels)
        labels_for_mixup = tf.gather(labels, permutation_order)

        lambda_sample = tf.reshape(lambda_sample, [-1, 1])
        labels = (
            lambda_sample * labels_smoothed + (1.0 - lambda_sample) * labels_for_mixup
        )

        return images, labels

    def _smooth_labels(self, labels):
        label_smoothing = self.label_smoothing or 0.0
        off_value = label_smoothing / tf.cast(tf.shape(labels)[1], tf.float32)
        on_value = 1.0 - label_smoothing + off_value
        return on_value * labels + (1 - labels) * off_value