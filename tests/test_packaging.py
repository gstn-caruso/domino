import configparser
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile


class PackagingTest(unittest.TestCase):
    def givenExportacionesValidas_whenEmpaquetarVersion_thenApkYDebCoherentes(self):
        repository = Path(__file__).resolve().parents[1]
        version = "1.2.3"
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            linux = workspace / "linux-export"
            linux.write_text("#!/bin/sh\nprintf 'domino-linux-fixture\\n'\n")
            linux.chmod(0o755)
            apk = workspace / "android-export.apk"
            # ZIP de transporte únicamente: no es una exportación Android válida.
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("fixture.txt", "domino-apk-transport-only")
            original_apk = apk.read_bytes()
            output = workspace / "release"

            packaged = subprocess.run(
                [
                    sys.executable, str(repository / "scripts/package.py"),
                    "--version", version, "--linux", str(linux),
                    "--apk", str(apk), "--output", str(output),
                ],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(
                packaged.returncode, 0,
                f"El empaquetador debe generar APK y DEB: {packaged.stderr}",
            )
            packaged_apk = output / f"domino-{version}.apk"
            deb = output / f"domino_{version}_amd64.deb"
            self.assertEqual(packaged_apk.read_bytes(), original_apk)
            self.assertTrue(deb.is_file(), f"Falta el paquete {deb.name}")
            for field, expected in (
                ("Package", "domino"), ("Version", version), ("Architecture", "amd64"),
            ):
                metadata = subprocess.run(
                    ["dpkg-deb", "--field", str(deb), field],
                    capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(metadata.returncode, 0, metadata.stderr)
                self.assertEqual(metadata.stdout.strip(), expected)

            extracted = workspace / "extracted"
            extraction = subprocess.run(
                ["dpkg-deb", "-x", str(deb), str(extracted)],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(extraction.returncode, 0, extraction.stderr)
            desktop_path = extracted / "usr/share/applications/domino.desktop"
            validation = subprocess.run(
                ["desktop-file-validate", str(desktop_path)],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            desktop = configparser.ConfigParser(interpolation=None)
            desktop.read(desktop_path)
            entry = desktop["Desktop Entry"]
            self.assertEqual(entry["Type"], "Application")
            self.assertTrue(entry["Name"].strip())
            self.assertIn(entry["Exec"], ("/usr/games/domino", "/usr/bin/domino"))
            self.assertEqual(entry["Icon"], "domino")
            launcher = extracted / entry["Exec"].lstrip("/")
            self.assertEqual(stat.S_IMODE(launcher.stat().st_mode), 0o755)
            execution = subprocess.run(
                [str(launcher)], cwd=extracted,
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout, "domino-linux-fixture\n")
            icons = [
                icon for icon in (extracted / "usr/share/icons/hicolor").glob("*/apps/domino.*")
                if icon.suffix in (".svg", ".png")
            ]
            self.assertTrue(icons, "El Icon=domino debe resolver a un icono instalado")
            for asset in [desktop_path, *icons]:
                self.assertGreater(asset.stat().st_size, 0)
                self.assertEqual(stat.S_IMODE(asset.stat().st_mode), 0o644)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        PackagingTest("givenExportacionesValidas_whenEmpaquetarVersion_thenApkYDebCoherentes"),
    ])


if __name__ == "__main__":
    unittest.main()
