#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Empaqueta las exportaciones de Dominó.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--linux", required=True, type=Path)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", args.version):
        parser.error("--version debe tener el formato X.Y.Z, con números sin ceros iniciales")
    for option, source in (("--linux", args.linux), ("--apk", args.apk)):
        if not source.is_file() or not os.access(source, os.R_OK):
            parser.error(f"{option} debe ser un archivo legible: {source}")
    if not os.access(args.linux, os.X_OK):
        parser.error(f"--linux debe ser ejecutable: {args.linux}")
    if args.output.exists() and not args.output.is_dir():
        parser.error(f"--output debe ser un directorio: {args.output}")
    if shutil.which("dpkg-deb") is None:
        parser.error("se necesita dpkg-deb para crear el paquete Debian")

    apk_name = f"domino-{args.version}.apk"
    deb_name = f"domino_{args.version}_amd64.deb"
    for name in (apk_name, deb_name):
        destination = args.output / name
        if destination.exists() or destination.is_symlink():
            parser.error(f"no se sobrescribirá el destino existente: {destination}")

    assets = Path(__file__).resolve().parents[1] / "packaging"
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".domino-package-", dir=args.output) as temporary:
            staging = Path(temporary)
            root = staging / "root"
            for directory in (
                "DEBIAN", "usr/games", "usr/share/applications",
                "usr/share/icons/hicolor/scalable/apps",
            ):
                (root / directory).mkdir(parents=True, exist_ok=True)

            launcher = root / "usr/games/domino"
            shutil.copyfile(args.linux, launcher)
            shutil.copyfile(assets / "domino.desktop", root / "usr/share/applications/domino.desktop")
            shutil.copyfile(assets / "domino.svg", root / "usr/share/icons/hicolor/scalable/apps/domino.svg")
            shutil.copytree(assets.parent / "third_party", root / "usr/share/doc/domino")
            (root / "DEBIAN/control").write_text(
                "Package: domino\n"
                f"Version: {args.version}\n"
                "Section: games\n"
                "Priority: optional\n"
                "Architecture: amd64\n"
                "Maintainer: Domino contributors\n"
                "Description: A calm domino application\n",
                encoding="utf-8",
            )
            root.chmod(0o755)
            for entry in root.rglob("*"):
                entry.chmod(0o755 if entry.is_dir() or entry == launcher else 0o644)

            shutil.copyfile(args.apk, staging / apk_name)
            subprocess.run(
                ["dpkg-deb", "--root-owner-group", "--build", str(root), str(staging / deb_name)],
                capture_output=True, text=True, check=True,
            )
            for name in (apk_name, deb_name):
                (staging / name).chmod(0o644)
                # Publish complete files without replacing an existing destination.
                os.link(staging / name, args.output / name)
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Error al crear el DEB: {error.stderr.strip()}\n")
    except OSError as error:
        parser.exit(1, f"Error de empaquetado: {error}\n")

    for name in (apk_name, deb_name):
        print(args.output / name)


if __name__ == "__main__":
    main()
