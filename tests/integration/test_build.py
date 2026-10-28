import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile


@unittest.skipUnless(os.environ.get("RUN_EXPORT_TESTS") == "1", "Requiere RUN_EXPORT_TESTS=1")
class BuildIntegrationTest(unittest.TestCase):
    def givenGodotEnPath_whenConstruirEntrega_thenUsaMotorDisponible(self):
        repository = Path(__file__).resolve().parents[2]
        godot = shutil.which(os.environ["GODOT_BIN"])
        self.assertIsNotNone(godot, "Falta el motor real para preparar el PATH")

        with tempfile.TemporaryDirectory(prefix="domino-path-test-") as temporary:
            workspace = Path(temporary)
            binaries = workspace / "bin"
            binaries.mkdir()
            (binaries / "godot").symlink_to(godot)
            environment = os.environ.copy()
            environment.update({
                "GODOT_BIN": "godot",
                "PATH": str(binaries) + os.pathsep + environment["PATH"],
            })
            output = workspace / "out"
            execution = subprocess.run(
                [
                    sys.executable, str(repository / "scripts/build.py"),
                    "--version", "0.1.7", "--version-code", "7",
                    "--output", str(output),
                ],
                cwd=repository, env=environment,
                capture_output=True, text=True, timeout=900,
            )
            self.assertEqual(
                execution.returncode, 0,
                f"Falló la construcción con Godot en PATH:\n{execution.stdout}\n{execution.stderr}",
            )
            for name in ("domino-0.1.7.apk", "domino_0.1.7_amd64.deb"):
                artifact = output / name
                self.assertTrue(artifact.is_file(), f"Falta el artefacto {name}")
                self.assertGreater(artifact.stat().st_size, 0)

    def givenProyectoGodot_whenConstruirEntrega_thenApkFirmadoYDebArrancable(self):
        repository = Path(__file__).resolve().parents[2]
        for variable in ("GODOT_BIN", "JAVA_HOME", "ANDROID_HOME"):
            self.assertTrue(os.environ.get(variable), f"Falta {variable} en el entorno")
        tools = Path(os.environ["ANDROID_HOME"]) / "build-tools/35.0.1"
        for executable in (
            Path(os.environ["GODOT_BIN"]),
            Path(os.environ["JAVA_HOME"]) / "bin/java",
            tools / "aapt",
            tools / "apksigner",
        ):
            self.assertTrue(
                executable.is_file() and os.access(executable, os.X_OK),
                f"Falta una herramienta ejecutable: {executable}",
            )
        self.assertIsNotNone(shutil.which("dpkg-deb"), "Falta dpkg-deb")

        def run(command, *, cwd=repository, timeout=30):
            execution = subprocess.run(
                [str(argument) for argument in command], cwd=cwd,
                capture_output=True, text=True, timeout=timeout,
            )
            self.assertEqual(
                execution.returncode, 0,
                f"Falló {command}:\n{execution.stdout}\n{execution.stderr}",
            )
            return execution

        with tempfile.TemporaryDirectory(prefix="domino-build-test-") as temporary:
            workspace = Path(temporary)
            output = workspace / "out"
            run(
                [
                    sys.executable, repository / "scripts/build.py",
                    "--version", "0.1.7", "--version-code", "7",
                    "--output", output,
                ],
                timeout=900,
            )

            apk = output / "domino-0.1.7.apk"
            deb = output / "domino_0.1.7_amd64.deb"
            for artifact in (apk, deb):
                self.assertTrue(artifact.is_file(), f"Falta el artefacto {artifact.name}")
                self.assertGreater(artifact.stat().st_size, 0)

            signature = run([tools / "apksigner", "verify", "--verbose", "--print-certs", apk])
            self.assertIn("CN=Android Debug", signature.stdout)
            badging = run([tools / "aapt", "dump", "badging", apk]).stdout
            self.assertRegex(
                badging,
                r"(?m)^package: name='io\.github\.gstncaruso\.domino\.preview' "
                r"versionCode='7' versionName='0\.1\.7'(?: |$)",
            )
            permissions = run([tools / "aapt", "dump", "permissions", apk]).stdout
            self.assertNotIn("android.permission.INTERNET", permissions)

            for field, expected in (
                ("Package", "domino"), ("Version", "0.1.7"), ("Architecture", "amd64"),
            ):
                with self.subTest(debian_field=field):
                    metadata = run(["dpkg-deb", "--field", deb, field])
                    self.assertEqual(metadata.stdout.strip(), expected)
            extracted = workspace / "extracted"
            run(["dpkg-deb", "--extract", deb, extracted])
            launcher = extracted / "usr/games/domino"
            self.assertTrue(
                launcher.is_file() and os.access(launcher, os.X_OK),
                "El Debian debe contener el ejecutable /usr/games/domino",
            )
            launched = run(
                [launcher, "--headless", "--quit-after", "2"],
                cwd=extracted, timeout=60,
            )
            self.assertNotRegex(launched.stdout + launched.stderr, r"\b(?:SCRIPT )?ERROR\b")

    def givenEntregaGodot_whenInspeccionarInstaladores_thenIncluyenLicenciasDelMotorYTerceros(self):
        repository = Path(__file__).resolve().parents[2]

        def run(command):
            execution = subprocess.run(
                [str(argument) for argument in command], cwd=repository,
                capture_output=True, text=True, timeout=900,
            )
            self.assertEqual(
                execution.returncode, 0,
                f"Falló {command}:\n{execution.stdout}\n{execution.stderr}",
            )

        with tempfile.TemporaryDirectory(prefix="domino-licenses-test-") as temporary:
            workspace = Path(temporary)
            output = workspace / "out"
            run([
                sys.executable, repository / "scripts/build.py",
                "--version", "0.1.7", "--version-code", "7", "--output", output,
            ])
            extracted = workspace / "extracted"
            run(["dpkg-deb", "--extract", output / "domino_0.1.7_amd64.deb", extracted])

            with ZipFile(output / "domino-0.1.7.apk") as apk:
                for name, markers in (
                    ("GODOT_LICENSE.txt", (b"Permission is hereby granted, free of charge",)),
                    ("GODOT_COPYRIGHT.txt", (b"Copyright", b"FreeType")),
                ):
                    with self.subTest(installer="DEB", notice=name):
                        installed = extracted / "usr/share/doc/domino" / name
                        self.assertTrue(
                            installed.is_file(),
                            f"El DEB no incluye /usr/share/doc/domino/{name}",
                        )
                        content = installed.read_bytes()
                        for marker in markers:
                            self.assertIn(marker, content)
                        self.assertEqual(content, (repository / "third_party" / name).read_bytes())
                    with self.subTest(installer="APK", notice=name):
                        asset = f"assets/third_party/{name}"
                        self.assertIn(
                            asset, apk.namelist(),
                            f"El APK no incluye {asset}",
                        )
                        content = apk.read(asset)
                        for marker in markers:
                            self.assertIn(marker, content)
                        self.assertEqual(content, (repository / "third_party" / name).read_bytes())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        BuildIntegrationTest("givenGodotEnPath_whenConstruirEntrega_thenUsaMotorDisponible"),
        BuildIntegrationTest("givenProyectoGodot_whenConstruirEntrega_thenApkFirmadoYDebArrancable"),
        BuildIntegrationTest("givenEntregaGodot_whenInspeccionarInstaladores_thenIncluyenLicenciasDelMotorYTerceros"),
    ])


if __name__ == "__main__":
    unittest.main()
