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
"""rand_augment_demo.py shows how to use the RandAugment preprocessing layer.

Uses the oxford_flowers102 dataset.  In this script the flowers
are loaded, then are passed through the preprocessing layers.
Finally, they are shown using matplotlib.
"""
import matplotlib.pyplot as plt
import tensorflow as tf
import tensorflow_datasets as tfds

from keras_cv.layers import preprocessing

IMG_SIZE = (224, 224)
BATCH_SIZE = 64


def resize(image, num_classes=10):
    image = tf.image.resize(image, IMG_SIZE)
    return image


def create_custom_pipeline():
    layers = preprocessing.RandAugment.get_standard_policy(
        value_range=(0, 255), magnitude=0.75, magnitude_stddev=0.3
    )
    layers = layers[:4]  # slice out some layers you don't want for whatever reason
    layers = layers + [preprocessing.GridMask()]
    return preprocessing.RandomAugmentationPipeline(
        layers=layers, augmentations_per_image=3
    )


def main():
    data, ds_info = tfds.load("oxford_flowers102", with_info=True, as_supervised=True)
    train_ds = data["train"]

    num_classes = ds_info.features["label"].num_classes

    train_ds = (
        train_ds.map(lambda x, y: resize(x, num_classes=num_classes))
        .shuffle(10 * BATCH_SIZE)
        .batch(BATCH_SIZE)
    )

    custom_pipeline = create_custom_pipeline()

    train_ds = train_ds.map(custom_pipeline, num_parallel_calls=tf.data.AUTOTUNE)

    for images in train_ds.take(1):
        plt.figure(figsize=(8, 8))
        for i in range(9):
            plt.subplot(3, 3, i + 1)
            plt.imshow(images[i].numpy().astype("uint8"))
            plt.axis("off")
        plt.show()


if __name__ == "__main__":
    main()
