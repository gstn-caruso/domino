#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Construye el APK preview y el DEB de Dominó.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", args.version):
        parser.error("--version debe tener el formato X.Y.Z, sin ceros iniciales")
    if not 1 <= args.version_code <= 2100000000:
        parser.error("--version-code debe estar entre 1 y 2100000000")
    for variable in ("GODOT_BIN", "JAVA_HOME", "ANDROID_HOME"):
        if not os.environ.get(variable):
            parser.error(f"falta {variable} en el entorno")
    if args.output.exists() and not args.output.is_dir():
        parser.error(f"--output debe ser un directorio: {args.output}")
    for name in (f"domino-{args.version}.apk", f"domino_{args.version}_amd64.deb"):
        destination = args.output / name
        if destination.exists() or destination.is_symlink():
            parser.error(f"no se sobrescribirá el destino existente: {destination}")

    repository = Path(__file__).resolve().parents[1]
    godot = shutil.which(os.environ["GODOT_BIN"])
    if godot is None:
        parser.error(f"no se encontró un ejecutable para GODOT_BIN: {os.environ['GODOT_BIN']}")
    java = Path(os.environ["JAVA_HOME"]).resolve()
    sdk = Path(os.environ["ANDROID_HOME"]).resolve()
    try:
        with tempfile.TemporaryDirectory(prefix="domino-build-") as temporary:
            workspace = Path(temporary)
            project = workspace / "project"
            project.mkdir()
            # Copy only application resources, never tests, metadata or prior builds.
            for name in ("project.godot", "main.gd", "main.gd.uid", "main.tscn"):
                shutil.copyfile(repository / name, project / name)
            shutil.copytree(repository / "translations", project / "translations")
            shutil.copytree(repository / "third_party", project / "third_party")
            presets = (repository / "export_presets.cfg").read_text(encoding="utf-8")
            presets = presets.replace("version/code=1", f"version/code={args.version_code}")
            presets = presets.replace('version/name="0.1.0"', f'version/name="{args.version}"')
            (project / "export_presets.cfg").write_text(presets, encoding="utf-8")

            config = workspace / "config"
            settings = config / "godot" / "editor_settings-4.7.tres"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                '[gd_resource type="EditorSettings" format=3]\n\n[resource]\n'
                f'export/android/android_sdk_path = {json.dumps(str(sdk))}\n'
                f'export/android/java_sdk_path = {json.dumps(str(java))}\n',
                encoding="utf-8",
            )
            # Public debug credentials only; the signing identity is new on each build.
            keystore = workspace / "debug.keystore"
            environment = os.environ.copy()
            environment.update({
                "XDG_CONFIG_HOME": str(config),
                "GODOT_ANDROID_KEYSTORE_DEBUG_PATH": str(keystore),
                "GODOT_ANDROID_KEYSTORE_DEBUG_USER": "androiddebugkey",
                "GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD": "android",
            })
            subprocess.run([
                str(java / "bin/keytool"), "-genkeypair", "-noprompt",
                "-keystore", str(keystore), "-storetype", "JKS",
                "-storepass", "android", "-keypass", "android",
                "-alias", "androiddebugkey", "-dname", "CN=Android Debug,O=Android,C=US",
                "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            ], env=environment, check=True)
            command = [godot, "--headless", "--path", str(project)]
            subprocess.run(command + ["--import"], env=environment, check=True)
            linux = workspace / "domino.x86_64"
            apk = workspace / "domino.apk"
            subprocess.run(command + ["--export-release", "Linux", str(linux)], env=environment, check=True)
            subprocess.run(command + ["--export-debug", "Android", str(apk)], env=environment, check=True)
            subprocess.run([
                sys.executable, str(repository / "scripts/package.py"),
                "--version", args.version, "--linux", str(linux), "--apk", str(apk),
                "--output", str(args.output.resolve()),
            ], check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error de construcción: {error}\n")


if __name__ == "__main__":
    main()
