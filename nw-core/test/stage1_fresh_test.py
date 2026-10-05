import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage1_fresh.py"
SPEC = importlib.util.spec_from_file_location("stage1_fresh", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
stage1_fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage1_fresh)


class Stage1FreshTests(unittest.TestCase):
    def test_committed_head_advance_invalidates_newer_than_sources_product(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "driver.elisa"
            source.parent.mkdir()
            source.write_text("def main() -> i64:\n    return 0\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Stage1 freshness test"], check=True)
            subprocess.run(["git", "-C", str(root), "add", "src/driver.elisa"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "fixture"],
                check=True,
                env={
                    **os.environ,
                    "GIT_AUTHOR_DATE": "2020-01-01T00:00:10Z",
                    "GIT_COMMITTER_DATE": "2020-01-01T00:00:10Z",
                },
            )
            product = root / "elisac-stage1"
            product.write_bytes(b"product")
            old = 1_577_836_801
            os.utime(source, (old, old))
            os.utime(product, (1_577_836_805, 1_577_836_805))

            self.assertEqual(stage1_fresh.stale_source(root, product), root / ".git/HEAD")


if __name__ == "__main__":
    unittest.main()
