import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


# gh accepts both --option=value and --option value; order is not contractual.
def arguments(call):
    return [part for argument in call["args"] for part in (
        argument.split("=", 1) if argument.startswith("--") else [argument]
    )]


def option(call, name, alias=None):
    args = arguments(call)
    for flag in (name, alias):
        if flag in args:
            return args[args.index(flag) + 1]
    return None


def write_fake_gh(path):
    # Fake only the network boundary; snapshot assets when they are attached.
    path.write_text(f"#!{sys.executable}\n" + '''import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
assets = {}
if args[:2] in (["release", "create"], ["release", "upload"]):
    value_flags = {"--repo", "-R", "--target", "--title", "-t", "--notes", "-n", "--notes-file", "-F", "--discussion-category"}
    skip = False
    for argument in args[2:]:
        if skip:
            skip = False
            continue
        if argument in value_flags:
            skip = True
            continue
        if argument.startswith("-"):
            continue
        asset = Path(argument.split("#", 1)[0])
        if asset.is_file():
            assets[asset.name] = asset.read_bytes().hex()
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps({"args": args, "assets": assets, "repo": os.environ.get("GH_REPO")}) + "\\n")
if args[:1] == ["api"]:
    normalized = [part for argument in args[1:] for part in (
        argument.split("=", 1) if argument.startswith("--") else [argument]
    )]
    endpoint = next((arg.lstrip("/") for arg in normalized if arg.lstrip("/").startswith("repos/")), "")
    if not endpoint.endswith(("/git/ref/tags/v0.1.42", "/git/refs/tags/v0.1.42")):
        sys.exit("Unsupported fake gh API endpoint: " + repr(args))
    for flag in ("--method", "-X"):
        if flag in normalized and normalized[normalized.index(flag) + 1] != "GET":
            sys.exit("Unsupported fake gh API method: " + repr(args))
    sha = os.environ.get("FAKE_TAG_COMMIT")
    if not sha:
        print("gh: Not Found (HTTP 404)", file=sys.stderr)
        sys.exit(1)
    response = {"ref": "refs/tags/v0.1.42", "object": {"type": "commit", "sha": sha}}
    query = next((normalized[normalized.index(flag) + 1] for flag in ("--jq", "-q") if flag in normalized), None)
    if query is None:
        print(json.dumps(response))
    elif query == ".object.sha":
        print(sha)
    else:
        sys.exit("Unsupported fake gh API query: " + repr(args))
    sys.exit(0)
if len(args) < 2 or args[0] != "release" or args[1] not in ("view", "create", "upload", "edit"):
    sys.exit("Unsupported fake gh command: " + repr(args))
if args[1] == "view":
    sys.exit(1)  # No previous release in these scenarios.
if args[1] in ("create", "edit"):
    print("https://github.com/gstn-caruso/domino/releases/tag/v0.1.42")
''')
    path.chmod(0o755)


class PublishTest(unittest.TestCase):
    def givenAmbosInstaladores_whenPublicarEntrega_thenReleaseContieneAmbosAntesDeHacerseVisible(self):
        repository = Path(__file__).resolve().parents[1]
        commit = "0123456789abcdef0123456789abcdef01234567"
        tag = "v0.1.42"
        github_repository = "gstn-caruso/domino"
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            artifacts = workspace / "artifacts"
            artifacts.mkdir()
            # Transport fixtures only; real export validity belongs to integration.
            installers = {
                "domino-0.1.42.apk": b"android-transport-fixture\n",
                "domino_0.1.42_amd64.deb": b"linux-transport-fixture\n",
            }
            for name, content in installers.items():
                (artifacts / name).write_bytes(content)
            log = workspace / "gh-calls.jsonl"
            binaries = workspace / "bin"
            binaries.mkdir()
            gh = binaries / "gh"
            write_fake_gh(gh)
            environment = {
                **os.environ,
                "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
                "GH_BIN": str(gh),
                "FAKE_GH_LOG": str(log),
            }

            execution = subprocess.run(
                [
                    sys.executable, str(repository / "scripts/publish.py"),
                    "--version", "0.1.42", "--commit", commit,
                    "--artifacts", str(artifacts), "--repo", github_repository,
                ],
                cwd=repository, env=environment,
                capture_output=True, text=True, timeout=10,
            )

            self.assertEqual(
                execution.returncode, 0,
                f"La CLI debe publicar ambos instaladores: {execution.stderr}",
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            creations = [call for call in calls if call["args"][:2] == ["release", "create"]]
            self.assertEqual(len(creations), 1, "Debe crear una entrega nueva")
            creation = creations[0]
            self.assertIn(tag, arguments(creation))
            self.assertEqual(option(creation, "--target"), commit)
            self.assertIn("--draft", arguments(creation), "La entrega debe nacer oculta")
            draft_index = arguments(creation).index("--draft")
            draft_value = arguments(creation)[draft_index + 1:draft_index + 2]
            self.assertNotEqual(draft_value, ["false"], "No debe crear una entrega pública")
            publications = [
                call for call in calls
                if call["args"][:2] == ["release", "edit"]
                and option(call, "--draft") == "false"
            ]
            self.assertEqual(len(publications), 1, "Debe hacer pública la entrega completa")
            publication = publications[0]
            self.assertLess(calls.index(creation), calls.index(publication))
            attached = {}
            for call in calls:
                if call["args"][1] in ("create", "upload", "edit"):
                    self.assertIn(tag, arguments(call))
                    self.assertEqual(
                        option(call, "--repo", "-R") or call["repo"], github_repository,
                    )
                if call is publication:
                    break
                attached.update(call["assets"])
            for name, content in installers.items():
                self.assertEqual(
                    attached.get(name), content.hex(),
                    f"{name} debe estar adjunto antes de hacer visible la entrega",
                )

    def givenTagDeOtroCommit_whenPublicarEntrega_thenRechazaSinCrearRelease(self):
        repository = Path(__file__).resolve().parents[1]
        commit = "0123456789abcdef0123456789abcdef01234567"
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            artifacts = workspace / "artifacts"
            artifacts.mkdir()
            original_files = {
                "domino-0.1.42.apk": b"android-transport-fixture\n",
                "domino_0.1.42_amd64.deb": b"linux-transport-fixture\n",
                "SHA256SUMS": b"existing manifest must remain unchanged\n",
            }
            for name, content in original_files.items():
                (artifacts / name).write_bytes(content)
            log = workspace / "gh-calls.jsonl"
            binaries = workspace / "bin"
            binaries.mkdir()
            gh = binaries / "gh"
            write_fake_gh(gh)
            environment = {
                **os.environ,
                "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
                "GH_BIN": str(gh),
                "FAKE_GH_LOG": str(log),
                "FAKE_TAG_COMMIT": "abcdef0123456789abcdef0123456789abcdef01",
            }

            execution = subprocess.run(
                [
                    sys.executable, str(repository / "scripts/publish.py"),
                    "--version", "0.1.42", "--commit", commit,
                    "--artifacts", str(artifacts), "--repo", "gstn-caruso/domino",
                ],
                cwd=repository, env=environment,
                capture_output=True, text=True, timeout=10,
            )

            self.assertEqual(
                {path.name: path.read_bytes() for path in artifacts.iterdir()},
                original_files,
                "Rechazar la entrega no debe mutar los instaladores ni el manifiesto",
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            mutations = [
                call["args"] for call in calls
                if call["args"][:2] in (
                    ["release", "create"], ["release", "edit"], ["release", "upload"],
                )
            ]
            self.assertNotIn("Unsupported fake gh", execution.stderr)
            self.assertNotEqual(
                execution.returncode, 0,
                f"Debe rechazar el tag de otro commit; efectos de publicación: {mutations}",
            )
            self.assertEqual(mutations, [], "No debe crear, editar ni adjuntar una release")

    def givenFaltaUnInstalador_whenPublicarEntrega_thenNoContactaGitHub(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            artifacts = workspace / "artifacts"
            artifacts.mkdir()
            (artifacts / "domino_0.1.42_amd64.deb").write_bytes(b"linux-transport-fixture\n")
            log = workspace / "gh-calls.jsonl"
            log.write_text("")
            binaries = workspace / "bin"
            binaries.mkdir()
            gh = binaries / "gh"
            write_fake_gh(gh)
            environment = {
                **os.environ,
                "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
                "GH_BIN": str(gh),
                "FAKE_GH_LOG": str(log),
            }

            execution = subprocess.run(
                [
                    sys.executable, str(repository / "scripts/publish.py"),
                    "--version", "0.1.42",
                    "--commit", "0123456789abcdef0123456789abcdef01234567",
                    "--artifacts", str(artifacts), "--repo", "gstn-caruso/domino",
                ],
                cwd=repository, env=environment,
                capture_output=True, text=True, timeout=10,
            )

            self.assertNotEqual(execution.returncode, 0, "No debe publicar sin el APK")
            self.assertIn("falta un instalador legible", execution.stderr)
            self.assertIn("domino-0.1.42.apk", execution.stderr)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(calls, [], "No debe contactar GitHub si falta un instalador")


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        PublishTest("givenAmbosInstaladores_whenPublicarEntrega_thenReleaseContieneAmbosAntesDeHacerseVisible"),
        PublishTest("givenTagDeOtroCommit_whenPublicarEntrega_thenRechazaSinCrearRelease"),
        PublishTest("givenFaltaUnInstalador_whenPublicarEntrega_thenNoContactaGitHub"),
    ])


if __name__ == "__main__":
    unittest.main()
