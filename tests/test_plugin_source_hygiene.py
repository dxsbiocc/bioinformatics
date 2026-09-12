from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class PluginSourceHygieneTests(unittest.TestCase):
    def test_plugin_source_excludes_local_transient_artifacts(self) -> None:
        forbidden_paths: list[pathlib.Path] = []
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            parts = set(relative.parts)
            if ".git" in parts or "__pycache__" in parts:
                continue
            if path.name in {".DS_Store", "Rplots.pdf"}:
                forbidden_paths.append(relative)
            if relative.parts[:1] in {(".tmp-tcga-preview",), ("figures",), ("results",)}:
                forbidden_paths.append(relative)

        self.assertEqual([], sorted({str(path) for path in forbidden_paths}))


if __name__ == "__main__":
    unittest.main()
