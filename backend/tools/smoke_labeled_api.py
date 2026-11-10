"""Actual API mechanics smoke on one Real and one Fake VALIDATION image.

Not an accuracy evaluation. Deletes only the history records this invocation
creates; never clears the user's history. No test-split access.
"""
import argparse
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path

import httpx
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8002")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.dataset_root.resolve(strict=True)
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(root):
        raise ValueError("Output must be new and outside dataset")
    results = []
    with httpx.Client(base_url=args.base_url, timeout=180, trust_env=False) as client:
        health_response = client.get("/api/v1/health")
        health_response.raise_for_status()
        health = health_response.json()
        if not health["model_loaded"]:
            raise RuntimeError("Active model is unavailable")
        for label in ("Real", "Fake"):
            path = next(iter(sorted((root / "Validation" / label).glob("*.jpg"))))
            content = path.read_bytes()
            with Image.open(BytesIO(content)) as image:
                image.verify()
            record_id = None
            row = {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(content).hexdigest(), "folder_label": label}
            try:
                response = client.post("/api/v1/predict", files={"file": (path.name, content, "image/jpeg")})
                response.raise_for_status()
                data = response.json()
                record_id = data["record_id"]
                assert abs(data["real_probability"] + data["fake_probability"] - 1) < 1e-6
                decision = "REAL" if data["real_probability"] >= data["threshold"] else "FAKE"
                assert data["predicted_class"] == decision
                assert abs(data["confidence_score"] - data["real_probability" if decision == "REAL" else "fake_probability"]) < 1e-6
                maps = {}
                for name in ("gradcam_heatmap", "gradcam_overlay"):
                    payload = data.get(name)
                    if payload:
                        encoded = payload.split(",", 1)[-1]
                        decoded = base64.b64decode(encoded, validate=True)
                        with Image.open(BytesIO(decoded)) as image:
                            assert image.format == "PNG"
                            maps[name] = {"format": image.format, "size": list(image.size), "bytes": len(decoded)}
                            image.verify()
                if not maps:
                    assert data.get("gradcam_error"), "Missing maps must have a diagnostic"
                detail = client.get(f"/api/v1/history/{record_id}")
                detail.raise_for_status()
                assert detail.json()["predicted_class"] == decision
                assert detail.json()["threshold"] == data["threshold"]
                row.update({key: value for key, value in data.items() if not key.startswith("gradcam_")})
                row.update(gradcam=maps, gradcam_error=data.get("gradcam_error"), history_verified=True,
                           agrees_with_folder_label=decision == label.upper())
            finally:
                if record_id is not None:
                    deletion = client.delete(f"/api/v1/history/{record_id}")
                    row["own_history_record_deleted"] = deletion.status_code == 204
                    deletion.raise_for_status()
                    assert client.get(f"/api/v1/history/{record_id}").status_code == 404
                results.append(row)
                output.write_text(json.dumps({"health": health, "scope": "Two validation images, mechanics only; not generalization accuracy or threshold selection", "results": results}, indent=2), encoding="utf-8")
    print(json.dumps({"health": health, "results": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
