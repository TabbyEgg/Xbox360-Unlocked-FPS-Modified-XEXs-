"""Transfer SHA-bound archive entries to Releases without committing binaries.

Only metadata and this publishing helper are committed. Archive bytes are
temporarily staged as uncommitted Git blob objects and immediately transferred
to durable release assets by a GitHub-hosted runner.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def gh(*args: str) -> bytes:
    result = subprocess.run(["gh", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace"))
    return result.stdout


def api(path: str, *, method: str | None = None, body: dict | None = None) -> dict | list:
    args = ["api", path]
    if method:
        args.extend(["--method", method])
    if body is None:
        return json.loads(gh(*args))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as file:
        json.dump(body, file)
        file.flush()
        return json.loads(gh(*args, "--input", file.name))


def safe_name(name: str) -> str:
    if not isinstance(name, str) or name in ("", ".", "..") or Path(name).name != name or "\\" in name:
        raise ValueError(f"Invalid asset name: {name!r}")
    return name


def verify(data: bytes, expected: dict, label: str) -> None:
    if len(data) != expected["size"] or digest(data) != expected["sha256"]:
        raise ValueError(f"Size or SHA-256 mismatch: {label}")


def main() -> None:
    manifest = json.loads(Path(".github/release-transfer.json").read_text())
    repo = os.environ["GH_REPO"]
    if manifest.get("version") != 1 or manifest.get("repository") != repo:
        raise ValueError("Transfer manifest does not match this repository")

    with tempfile.TemporaryDirectory(prefix="release-transfer-") as temp:
        root = Path(temp)
        prepared = []
        for index, release in enumerate(manifest["releases"]):
            if not re.fullmatch(r"[A-Za-z0-9._-]+", release["tag"]):
                raise ValueError("Invalid release tag")
            source = release["source"]
            if not re.fullmatch(r"[a-f0-9]{40}", source["blob_sha"]):
                raise ValueError("Invalid source blob SHA")
            if source["size"] > 100 * 1024 * 1024:
                raise ValueError("Source archive exceeds the transfer limit")
            blob = api(f"repos/{repo}/git/blobs/{source['blob_sha']}")
            if blob["encoding"] != "base64":
                raise ValueError("Unsupported Git blob encoding")
            archive = base64.b64decode("".join(blob["content"].split()), validate=True)
            verify(archive, source, release["tag"])

            directory = root / str(index)
            directory.mkdir()
            assets: dict[str, dict] = {}
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                entries = bundle.infolist()
                if len(entries) > 1024 or sum(entry.file_size for entry in entries) > 512 * 1024 * 1024:
                    raise ValueError("Archive extraction limit exceeded")
                names = [entry.filename for entry in entries]
                if len(names) != len(set(names)):
                    raise ValueError("Duplicate archive entries")
                if bundle.testzip() is not None:
                    raise ValueError("Archive CRC check failed")
                for entry in release["assets"]:
                    name = safe_name(entry["name"])
                    if name in {"README.md", "SHA256SUMS.txt"} or name in assets or entry["size"] > 64 * 1024 * 1024:
                        raise ValueError("Duplicate or oversized output asset")
                    info = bundle.getinfo(entry["archive_path"])
                    if info.is_dir() or info.file_size != entry["size"]:
                        raise ValueError("Invalid selected archive entry")
                    data = bundle.read(info)
                    verify(data, entry, name)
                    (directory / name).write_bytes(data)
                    assets[name] = {"size": len(data), "sha256": digest(data)}

            if release.get("archive_asset_name"):
                name = safe_name(release["archive_asset_name"])
                if name in {"README.md", "SHA256SUMS.txt"} or name in assets:
                    raise ValueError("Duplicate archive asset name")
                (directory / name).write_bytes(archive)
                assets[name] = {"size": len(archive), "sha256": digest(archive)}
            readme = release["notes"].encode()
            (directory / "README.md").write_bytes(readme)
            assets["README.md"] = {"size": len(readme), "sha256": digest(readme)}
            sums = "".join(f"{item['sha256']}  {name}\n" for name, item in sorted(assets.items())).encode()
            (directory / "SHA256SUMS.txt").write_bytes(sums)
            assets["SHA256SUMS.txt"] = {"size": len(sums), "sha256": digest(sums)}
            prepared.append((release, directory, assets))
            print(f"Verified {release['tag']}: {len(assets)} assets", flush=True)

        if os.environ.get("RELEASE_VERIFY_ONLY") == "1":
            print("Verification complete; no releases changed.")
            return

        # Validate all transfer data before creating or publishing any release.
        existing = api(f"repos/{repo}/releases?per_page=100")
        summary = []
        for release, directory, assets in prepared:
            matches = [item for item in existing if item["tag_name"] == release["tag"]]
            if len(matches) > 1:
                raise ValueError("Duplicate release tags")
            metadata = {"name": release["title"], "body": release["notes"],
                        "prerelease": release.get("prerelease", False), "make_latest": "false"}
            if matches:
                remote = matches[0]
            else:
                remote = api(f"repos/{repo}/releases", method="POST", body={
                    **metadata, "tag_name": release["tag"],
                    "target_commitish": os.environ["GITHUB_SHA"], "draft": True})

            current = {item["name"]: item for item in remote["assets"]}
            for name, item in assets.items():
                if name in current:
                    prior = current[name]
                    data = gh("api", f"repos/{repo}/releases/assets/{prior['id']}",
                              "-H", "Accept: application/octet-stream")
                    if name in {"README.md", "SHA256SUMS.txt"} and (len(data) != item["size"] or digest(data) != item["sha256"]):
                        # Documentation and checksums evolve as variants are added.
                        # Binary assets remain immutable and must match exactly.
                        gh("release", "upload", release["tag"], str(directory / name), "--clobber", "--repo", repo)
                    else:
                        verify(data, item, f"Existing release asset {name}")
                    continue
                gh("release", "upload", release["tag"], str(directory / name), "--repo", repo)

            remote = api(f"repos/{repo}/releases/{remote['id']}")
            uploaded = {item["name"]: item for item in remote["assets"]}
            for name, expected in assets.items():
                item = uploaded.get(name)
                if not item or item["state"] != "uploaded" or item["size"] != expected["size"]:
                    raise ValueError(f"Incomplete uploaded asset: {name}")
                if item.get("digest") and item["digest"] != "sha256:" + expected["sha256"]:
                    raise ValueError(f"Uploaded checksum mismatch: {name}")
                if not item.get("digest"):
                    downloaded = gh("api", f"repos/{repo}/releases/assets/{item['id']}",
                                    "-H", "Accept: application/octet-stream")
                    verify(downloaded, expected, f"Uploaded release asset {name}")

            remote = api(f"repos/{repo}/releases/{remote['id']}", method="PATCH",
                         body={**metadata, "draft": False})
            summary.append(f"- [{release['title']}]({remote['html_url']}) — {len(assets)} assets")
            print(f"Published {release['tag']}: {remote['html_url']}", flush=True)

        result = "## Game releases\n\n" + "\n".join(summary) + "\n"
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as file:
                file.write(result)
        print(result)


if __name__ == "__main__":
    main()
