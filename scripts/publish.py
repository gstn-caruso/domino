#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Publica la preview de Dominó con ambos instaladores.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()

    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", args.version):
        parser.error("--version debe tener el formato X.Y.Z, sin ceros iniciales")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.commit):
        parser.error("--commit debe ser un SHA de 40 caracteres hexadecimales")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*", args.repo):
        parser.error("--repo debe tener el formato propietario/repositorio")
    installers = [
        args.artifacts.resolve() / f"domino-{args.version}.apk",
        args.artifacts.resolve() / f"domino_{args.version}_amd64.deb",
    ]
    for installer in installers:
        if not installer.is_file() or not os.access(installer, os.R_OK):
            parser.error(f"falta un instalador legible: {installer}")

    gh = os.environ.get("GH_BIN", "gh")
    tag = f"v{args.version}"
    try:
        # Read both complete inputs before contacting GitHub. The manifest is
        # temporary, so an existing file in --artifacts is never overwritten.
        checksums = []
        for installer in installers:
            with installer.open("rb") as source:
                if not source.read(1):
                    parser.error(f"el instalador está vacío: {installer}")
                source.seek(0)
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            checksums.append(f"{digest}  {installer.name}\n")

        with tempfile.TemporaryDirectory(prefix="domino-publish-") as temporary:
            manifest = Path(temporary) / "SHA256SUMS"
            manifest.write_text("".join(checksums), encoding="utf-8")
            existing = subprocess.run(
                [gh, "release", "view", tag, "--repo", args.repo],
                capture_output=True, text=True,
            )
            # Never resume or overwrite an existing release, even a draft.
            if existing.returncode == 0:
                parser.exit(1, f"Conflicto: ya existe la release {tag}; no se modificará.\n")
            if existing.returncode != 1 or (
                existing.stderr.strip() and "release not found" not in existing.stderr.lower()
            ):
                parser.exit(1, f"No se pudo comprobar la release: {existing.stderr.strip()}\n")

            reference = subprocess.run(
                [gh, "api", f"repos/{args.repo}/git/ref/tags/{tag}"],
                capture_output=True, text=True,
            )
            if reference.returncode != 0:
                if reference.returncode != 1 or "(HTTP 404)" not in reference.stderr:
                    parser.exit(1, f"No se pudo comprobar el tag {tag}: {reference.stderr.strip()}\n")
            else:
                try:
                    tag_object = json.loads(reference.stdout)["object"]
                    tag_type = tag_object["type"]
                    tag_commit = tag_object["sha"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    parser.exit(1, f"No se pudo interpretar el tag {tag}; no se publicará.\n")
                if tag_type != "commit":
                    parser.exit(1, f"El tag {tag} no apunta directamente a un commit; no se publicará sin resolverlo.\n")
                if not isinstance(tag_commit, str) or tag_commit.lower() != args.commit.lower():
                    parser.exit(1, f"Conflicto: el tag {tag} no corresponde al commit {args.commit}; no se publicará.\n")

            subprocess.run([
                gh, "release", "create", tag, "--repo", args.repo,
                "--target", args.commit, "--draft", "--prerelease",
                "--title", f"Dominó {args.version} — preview",
                "--notes", (
                    "Preview del menú y la base; todavía no incluye una partida. "
                    "Incluye instaladores APK para Android y DEB para Linux amd64.\n\n"
                    "El APK es debug, firmado con una clave efímera de esta construcción: "
                    "no es una entrega para Google Play y puede requerir desinstalar "
                    "la preview anterior antes de instalar.\n\n"
                    "Comprueba ambos instaladores con: sha256sum -c SHA256SUMS\n"
                    f"Commit: {args.commit}"
                ),
                *(str(installer) for installer in installers), str(manifest),
            ], capture_output=True, text=True, check=True)
            # gh create returns only after all attachments have been uploaded.
            subprocess.run([
                gh, "release", "edit", tag, "--repo", args.repo, "--draft=false",
            ], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Error de publicación; revisa si quedó un borrador: {error.stderr.strip()}\n")
    except OSError as error:
        parser.exit(1, f"Error de publicación: {error}\n")


if __name__ == "__main__":
    main()
