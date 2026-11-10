"""Image preprocessing aligned with the existing Colab/backend inference contract."""
import numpy as np
import tensorflow as tf
from PIL import Image


def preprocess_image(image: Image.Image) -> np.ndarray:
    """Return float32 RGB (1, 224, 224, 3), preserving the 0–255 scale.

    Keep TensorFlow's default bilinear resize (no antialiasing), matching the
    previously effective implementation. EfficientNet rescales inside the model.
    No EXIF rotation, cropping, or extra /255 normalization is applied here.
    """
    array = np.asarray(image.convert("RGB"), dtype=np.float32)
    resized = tf.image.resize(array, (224, 224), method="bilinear", antialias=False)
    return tf.expand_dims(resized, axis=0).numpy()
