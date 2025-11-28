import shutil
import sys
import tempfile
import types
from pathlib import Path
import unittest

# Avoid optional runtime deps during import.
sys.modules.setdefault("uvloop", types.SimpleNamespace())
sys.modules.setdefault(
    "patoolib",
    types.SimpleNamespace(
        extract_archive=lambda *args, **kwargs: None,
        util=types.SimpleNamespace(PatoolError=Exception),
    ),
)

from pytalk.tools import ttsdk_downloader


class MoveProEditionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = Path(tempfile.mkdtemp())
        # Backup and override module-level cd used by the downloader.
        self.original_cd = ttsdk_downloader.cd
        ttsdk_downloader.cd = self.tempdir

        # Build minimal extracted layout expected by move().
        extracted = self.tempdir / "ttsdk" / "tt5prosdk_v5.19a_win64"
        dll_dir = extracted / "Library" / "TeamTalk_DLL"
        dll_dir.mkdir(parents=True, exist_ok=True)
        # Create pro-only binaries.
        (dll_dir / "TeamTalk5Pro.dll").write_bytes(b"dummy")
        (dll_dir / "libTeamTalk5Pro.so").write_bytes(b"dummy")
        (dll_dir / "libTeamTalk5Pro.dylib").write_bytes(b"dummy")
        # Minimal TeamTalkPy folder to satisfy move().
        tpy_dir = extracted / "Library" / "TeamTalkPy"
        tpy_dir.mkdir(parents=True, exist_ok=True)
        (tpy_dir / "__init__.py").write_bytes(b"")

    def tearDown(self) -> None:
        ttsdk_downloader.cd = self.original_cd
        shutil.rmtree(self.tempdir)

    def test_move_copies_pro_binaries_to_legacy_names(self) -> None:
        ttsdk_downloader.move("pro")
        impl_dir = self.tempdir / "implementation" / "TeamTalk_DLL"
        self.assertTrue((impl_dir / "TeamTalk5.dll").exists())
        self.assertTrue((impl_dir / "libTeamTalk5.so").exists())
        self.assertTrue((impl_dir / "libTeamTalk5.dylib").exists())
        # Ensure originals are preserved.
        self.assertTrue((impl_dir / "TeamTalk5Pro.dll").exists())


if __name__ == "__main__":
    unittest.main()
