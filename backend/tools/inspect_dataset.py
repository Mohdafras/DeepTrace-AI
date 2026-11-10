"""Read-only, exhaustive dataset integrity inventory; never executes dataset code.

Run with Python -I -B. Writes only to a NEW report directory outside the dataset.
Test images are decoded/hashed for integrity only, never scored by a model here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import time
import warnings

from PIL import Image

SPLITS = {"train": "train", "training": "train", "validation": "validation", "valid": "validation", "val": "validation", "test": "test", "testing": "test"}
LABELS = {"fake": 0, "real": 1}
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
API_FORMATS = {"JPEG", "PNG", "WEBP"}


def write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def inspect_one(item):
    path, relative, split, label = item
    row = {"path": relative, "split": split, "label": label, "label_name": {0: "Fake", 1: "Real"}.get(label),
           "extension": path.suffix.lower(), "valid": False}
    try:
        if path.is_symlink():
            raise ValueError("Symlink file is not accepted")
        stat = path.stat()
        row.update(bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)
        content = path.read_bytes()
        row["sha256"] = hashlib.sha256(content).hexdigest()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                row.update(format=image.format, width=image.width, height=image.height, mode=image.mode,
                           frames=getattr(image, "n_frames", 1))
                if image.width * image.height > 20_000_000:
                    raise ValueError("Exceeds backend 20 megapixel limit")
                if getattr(image, "is_animated", False):
                    raise ValueError("Animated image is unsupported")
                image.verify()
            with Image.open(BytesIO(content)) as image:
                row["exif_orientation"] = image.getexif().get(274)
                rgb = image.convert("RGB")
                rgb.load()  # Verify compressed pixel content as well as container headers.
                h = hashlib.sha256(f"RGB:{rgb.width}x{rgb.height}:".encode())
                h.update(rgb.tobytes())
                row["pixel_sha256"] = h.hexdigest()
        row["api_supported"] = row["format"] in API_FORMATS and row["extension"] in {".jpg", ".jpeg", ".png", ".webp"}
        row["valid"] = True
        if split is None or label is None:
            row["label_error"] = "Unknown or ambiguous split/class folder; not inferred from filenames"
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def discover(root: Path):
    items, directories, layout_errors = [], [], []
    def traversal_error(error):
        layout_errors.append(f"Unreadable directory: {error.filename}: {error}")
    for current, dirs, files in os.walk(root, followlinks=False, onerror=traversal_error):
        base = Path(current)
        for name in list(dirs):
            child = base / name
            directories.append(child.relative_to(root).as_posix())
            if child.is_symlink():
                layout_errors.append(f"Symlink directory excluded: {child.relative_to(root)}")
                dirs.remove(name)
        for name in sorted(files):
            path = base / name
            relative = path.relative_to(root)
            parents = [p.casefold() for p in relative.parts[:-1]]
            split_names = [SPLITS[p] for p in parents if p in SPLITS]
            label_names = [LABELS[p] for p in parents if p in LABELS]
            split = split_names[0] if len(split_names) == 1 else None
            label = label_names[0] if len(label_names) == 1 else None
            items.append((path, relative.as_posix(), split, label))
    return sorted(items, key=lambda x: x[1]), directories, layout_errors


def duplicate_groups(rows, key):
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        if row.get(key):
            groups[row[key]].append(index)
    result = []
    for digest, indices in groups.items():
        if len(indices) > 1:
            members = [rows[i] for i in indices]
            result.append({"hash": digest, "count": len(members),
                           "cross_split": len({r["split"] for r in members}) > 1,
                           "conflicting_labels": len({r["label"] for r in members}) > 1,
                           "paths": [r["path"] for r in members]})
    return result


def inspect(root: Path, output: Path, workers: int = 4):
    root = root.resolve(strict=True)
    output = output.resolve()
    if not root.is_dir():
        raise ValueError("Dataset root must be a directory")
    if output.exists() or output == root or output.is_relative_to(root):
        raise ValueError("Report output must be NEW and outside the dataset")
    if not output.parent.is_dir():
        raise ValueError("Report parent must already exist")
    started = time.monotonic()
    items, directories, layout_errors = discover(root)
    output.mkdir()
    write_json(output / "inspection_started.json", {"dataset_root": str(root), "files_discovered": len(items),
               "created_utc": datetime.now(timezone.utc).isoformat(), "workers": workers,
               "read_only": True, "interruption": "Partial inventory.jsonl is preserved; rerun to a new output directory."})
    print(f"Discovered {len(items):,} files. Exhaustive decoding and SHA-256 inspection starting.", flush=True)
    rows = []
    with (output / "inventory.jsonl").open("x", encoding="utf-8") as stream, ThreadPoolExecutor(max_workers=workers) as executor:
        # Bound outstanding work and decoded image memory; no full dataset pixel cache.
        for start in range(0, len(items), 512):
            for row in executor.map(inspect_one, items[start:start + 512]):
                rows.append(row)
                stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
            if start % 5120 == 0 or start + 512 >= len(items):
                print(f"Inspected {len(rows):,}/{len(items):,} files in {time.monotonic()-started:.1f}s", flush=True)
    exact = duplicate_groups(rows, "sha256")
    pixels = duplicate_groups(rows, "pixel_sha256")
    invalid = [r for r in rows if not r["valid"]]
    unlabelled = [r["path"] for r in rows if r["split"] is None or r["label"] is None]
    counts = {}
    for split in ("train", "validation", "test"):
        counts[split] = {}
        for label, name in ((0, "Fake"), (1, "Real")):
            selected = [r for r in rows if r["split"] == split and r["label"] == label]
            counts[split][name] = {"files": len(selected), "valid_images": sum(r["valid"] for r in selected),
                                   "invalid_files": sum(not r["valid"] for r in selected),
                                   "bytes": sum(r.get("bytes", 0) for r in selected)}
            if not selected:
                layout_errors.append(f"Missing or empty split/class: {split}/{name}")
    report = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
              "dataset_root": str(root), "elapsed_seconds": time.monotonic()-started,
              "total_files": len(rows), "valid_images": sum(r["valid"] for r in rows),
              "total_bytes": sum(r.get("bytes", 0) for r in rows), "counts": counts,
              "extensions": dict(Counter(r["extension"] for r in rows)),
              "decoded_formats": dict(Counter(r.get("format", "unreadable") for r in rows)),
              "dimensions": dict(Counter(f"{r['width']}x{r['height']}" for r in rows if r.get("width"))),
              "invalid_file_count": len(invalid), "unlabelled_files": unlabelled, "layout_errors": layout_errors,
              "class_imbalance_ratio_fake_over_real": {s: counts[s]["Fake"]["valid_images"] / counts[s]["Real"]["valid_images"] if counts[s]["Real"]["valid_images"] else None for s in counts},
              "duplicate_summary": {kind: {"groups": len(groups), "extra_copies": sum(g["count"]-1 for g in groups),
                  "cross_split_groups": sum(g["cross_split"] for g in groups),
                  "conflicting_label_groups": sum(g["conflicting_labels"] for g in groups)} for kind, groups in (("file_sha256", exact), ("decoded_rgb_sha256", pixels))},
              "api_unsupported_valid_images": sum(r["valid"] and not r.get("api_supported", False) for r in rows),
              "label_provenance": "Directory labels Fake=0, Real=1. Authenticity and source/identity separation are not independently verified.",
              "limitations": ["Hashes detect byte-identical and identical decoded RGB pixels, not near-duplicates, shared identities, or common source videos.",
                              "Integrity reads include Test. No model inference or training is performed.",
                              "Original dataset files are never written, moved, or removed."]}
    write_json(output / "inspection.json", report)
    write_json(output / "invalid_files.json", invalid)
    write_json(output / "duplicates.json", {"file_sha256": exact, "decoded_rgb_sha256": pixels})
    write_json(output / "directories.json", directories)
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("workers must be between 1 and 16")
    inspect(args.dataset_root, args.output_dir, args.workers)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    main()
