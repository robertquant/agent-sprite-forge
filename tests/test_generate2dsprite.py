from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "generate2dsprite" / "scripts" / "generate2dsprite.py"


def load_sprite_module():
    spec = importlib.util.spec_from_file_location("generate2dsprite", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Generate2dSpriteTests(unittest.TestCase):
    def test_split_grid_covers_non_divisible_image_dimensions(self) -> None:
        module = load_sprite_module()
        img = Image.new("RGBA", (101, 99), (255, 0, 255, 255))

        frames, metadata = module.split_grid(
            img,
            rows=2,
            cols=2,
            cell_size=16,
            threshold=100,
            edge_threshold=150,
            trim_border_px=0,
            edge_clean_depth=0,
        )

        self.assertEqual(len(frames), 4)
        self.assertEqual(metadata[0]["source_box"], [0, 0, 50, 50])
        self.assertEqual(metadata[-1]["source_box"], [50, 50, 101, 99])

    def test_process_rejects_invalid_mode_for_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw = tmp_path / "raw.png"
            Image.new("RGBA", (64, 64), (255, 0, 255, 255)).save(raw)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "process",
                    "--input",
                    str(raw),
                    "--target",
                    "player",
                    "--mode",
                    "projectile",
                    "--output-dir",
                    str(tmp_path / "out"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Mode 'projectile' is invalid for target 'player'", result.stderr)

    def test_process_sheet_requires_explicit_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw = tmp_path / "raw.png"
            Image.new("RGBA", (64, 64), (255, 0, 255, 255)).save(raw)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "process",
                    "--input",
                    str(raw),
                    "--target",
                    "asset",
                    "--mode",
                    "sheet",
                    "--output-dir",
                    str(tmp_path / "out"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Mode 'sheet' requires explicit --rows and --cols", result.stderr)

    def test_process_custom_sheet_writes_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw = tmp_path / "raw.png"
            Image.new("RGBA", (101, 99), (255, 0, 255, 255)).save(raw)
            out_dir = tmp_path / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "process",
                    "--input",
                    str(raw),
                    "--target",
                    "asset",
                    "--mode",
                    "sheet",
                    "--rows",
                    "2",
                    "--cols",
                    "2",
                    "--output-dir",
                    str(out_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads((out_dir / "pipeline-meta.json").read_text())
            self.assertEqual(metadata["rows"], 2)
            self.assertEqual(metadata["cols"], 2)
            self.assertEqual(metadata["frames"][-1]["source_box"], [50, 50, 101, 99])
            self.assertTrue((out_dir / "sheet-transparent.png").exists())


if __name__ == "__main__":
    unittest.main()
