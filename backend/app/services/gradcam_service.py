"""Class-specific Grad-CAM: a visual attention aid, not forensic proof."""
import base64
from io import BytesIO
from typing import Any

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image


def _last_conv_layer(model: Any) -> tuple[Any, Any]:
    """Return the owner and last Conv2D in graph layer order."""
    found = None
    for layer in model.layers:
        if isinstance(layer, tf.keras.Model):
            try:
                found = _last_conv_layer(layer)
            except ValueError:
                pass
        elif isinstance(layer, tf.keras.layers.Conv2D):
            found = (model, layer)
    if found is None:
        raise ValueError("No Conv2D layer was found in the loaded model.")
    return found


def _attention_map(model: Any, batch: np.ndarray, predicted_real: bool) -> np.ndarray:
    owner, layer = _last_conv_layer(model)
    if owner is model:
        grad_model = tf.keras.Model(model.inputs[0], [layer.output, model.outputs[0]])
    else:
        # The saved model is Input -> frozen EfficientNet -> pooling -> dropout
        # -> sigmoid. Reconnect that exact tail, without changing any weights.
        backbone_graph = tf.keras.Model(owner.inputs[0], [layer.output, owner.outputs[0]])
        try:
            owner_index = model.layers.index(owner)
        except ValueError as exc:
            raise RuntimeError("Grad-CAM requires a directly nested backbone.") from exc
        def grad_model(inputs, training=False):
            # Augmentation in this export precedes the backbone. Replay it with
            # training=False, exactly as in model inference (no augmentation).
            for prefix_layer in model.layers[:owner_index]:
                if not isinstance(prefix_layer, tf.keras.layers.InputLayer):
                    inputs = prefix_layer(inputs, training=training)
            conv, prediction = backbone_graph(inputs, training=training)
            for classifier_layer in model.layers[owner_index + 1:]:
                prediction = classifier_layer(prediction, training=training)
            return conv, prediction

    inputs = tf.convert_to_tensor(batch)
    with tf.GradientTape() as tape:
        # Explicit input watching also supports a completely frozen graph.
        tape.watch(inputs)
        conv_output, predictions = grad_model(inputs, training=False)
        score = predictions[:, 0] if predicted_real else 1.0 - predictions[:, 0]
    gradients = tape.gradient(score, conv_output)
    if gradients is None:
        raise RuntimeError("Grad-CAM target is disconnected from the selected class score.")
    weights = tf.reduce_mean(gradients, axis=(1, 2), keepdims=True)
    heatmap = tf.nn.relu(tf.reduce_sum(conv_output * weights, axis=-1))[0].numpy()
    if not np.isfinite(heatmap).all():
        raise RuntimeError("Grad-CAM produced non-finite attention values.")
    maximum = float(np.max(heatmap))
    if maximum <= 0:
        raise RuntimeError("No positive Grad-CAM activation for the predicted class.")
    return heatmap / maximum


def _encode_png(array: np.ndarray) -> str:
    output = BytesIO()
    Image.fromarray(array).save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def generate_gradcam_images(model: Any, batch: np.ndarray, original: Image.Image,
                            predicted_real: bool) -> dict[str, str]:
    """Return separate PNGs using a pale-to-dark blue relative-attention scale.

    Bound visual output dimensions; this does not change the 224px model input.
    Images are returned in memory and never written to history or disk.
    """
    heatmap = _attention_map(model, batch, predicted_real)
    visual = original.convert("RGB")
    visual.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    rgb = np.asarray(visual)
    resized = np.clip(cv2.resize(heatmap, (visual.width, visual.height)), 0, 1)
    low, high = np.array([239, 246, 255]), np.array([30, 64, 175])
    colored = np.rint(low + resized[..., None] * (high - low)).astype(np.uint8)
    overlay = cv2.addWeighted(rgb, 0.60, colored, 0.40, 0)
    return {"heatmap": _encode_png(colored), "overlay": _encode_png(overlay)}


def generate_gradcam(model: Any, batch: np.ndarray, original: Image.Image, predicted_real: bool) -> str:
    """Backward-compatible overlay helper."""
    return generate_gradcam_images(model, batch, original, predicted_real)["overlay"]
