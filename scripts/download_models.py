"""Download the demo models (network). Run on the GPU server, ideally in tmux:

    python scripts/download_models.py [--only sdxl,vae] [--probe-seconds 8]

Integrity is anchored to Hugging Face, whatever the byte source (ADR-0009):
- the revision is the pinned one in configs/demo.yaml, else the one already in
  models/MANIFEST.json, else the repo's current commit (then recorded);
- the expected hash of each file comes from the HF API at that revision (LFS sha256, or the
  git blob sha1 for small files), read through HF_ENDPOINT (default https://hf-mirror.com).

Bytes come from the fastest candidate source per model: the HF mirror at the pinned revision,
or the ModelScope copy of the same repo. Each source is probed with a short multi-connection
aria2c download; downloads use aria2c -c (resumable). A file that fails verification from one
source is retried from the next; the source used for every file is recorded in the manifest.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from omegaconf import OmegaConf

ROOT = Path(__file__).resolve().parents[1]
HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com").rstrip("/")
MS_ENDPOINT = "https://www.modelscope.cn"
ARIA = ["aria2c", "-q", "-c", "--file-allocation=none", "-x16", "-s16", "-k2M",
        "--max-tries=5", "--retry-wait=3", "--auto-file-renaming=false"]
MIN_OK_MBPS = 10.0


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "pinstyle-download/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def verify(path: Path, expect: dict) -> bool:
    if not path.is_file() or path.stat().st_size != expect["size"]:
        return False
    if "sha256" in expect:
        return sha256(path) == expect["sha256"]
    return git_blob_sha1(path) == expect["git_sha1"]


def hf_files(repo: str, revision: str, allow: list[str]) -> dict[str, dict]:
    info = get_json(f"{HF_ENDPOINT}/api/models/{repo}/revision/{revision}?blobs=true")
    out = {}
    for s in info["siblings"]:
        name = s["rfilename"]
        if not any(fnmatch.fnmatch(name, p) for p in allow):
            continue
        lfs = s.get("lfs")
        out[name] = ({"size": lfs["size"], "sha256": lfs["sha256"]} if lfs
                     else {"size": s["size"], "git_sha1": s["blobId"]})
    missing = [p for p in allow if not any(fnmatch.fnmatch(n, p) for n in out)]
    if missing:
        raise RuntimeError(f"{repo}@{revision}: no files match {missing}")
    return out


def source_urls(spec, revision: str, name: str) -> dict[str, str]:
    urls = {"hf-mirror": f"{HF_ENDPOINT}/{spec.repo}/resolve/{revision}/{name}"}
    if spec.get("modelscope"):
        urls["modelscope"] = f"{MS_ENDPOINT}/models/{spec.modelscope}/resolve/master/{name}"
    return urls


def probe(url: str, seconds: int) -> float:
    """MB/s over a short resumable-download probe (0 on failure)."""
    tmp = Path(tempfile.mkdtemp(prefix="probe_"))
    t0 = time.monotonic()
    try:
        subprocess.run([*ARIA, "-d", str(tmp), "-o", "f", url], timeout=seconds,
                       capture_output=True)
    except subprocess.TimeoutExpired:
        pass
    dt = time.monotonic() - t0
    got = sum(p.stat().st_size for p in tmp.rglob("*") if p.is_file())
    shutil.rmtree(tmp, ignore_errors=True)
    return got / dt / 2**20


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([*ARIA, "-d", str(dest.parent), "-o", dest.name, url], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated model keys")
    ap.add_argument("--probe-seconds", type=int, default=8)
    args = ap.parse_args()

    cfg = OmegaConf.load(ROOT / "configs" / "demo.yaml")
    models_dir = ROOT / cfg.paths.models
    models_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = models_dir / "MANIFEST.json"
    manifest: dict = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    only = {k for k in args.only.split(",") if k}

    for key, spec in cfg.models.items():
        if only and key not in only:
            continue
        revision = (spec.get("revision") or manifest.get(key, {}).get("revision")
                    or get_json(f"{HF_ENDPOINT}/api/models/{spec.repo}")["sha"])
        expected = hf_files(spec.repo, revision, list(spec.allow))
        local = models_dir / key
        todo = [n for n in expected if not verify(local / n, expected[n])]

        order = ["hf-mirror"]
        speeds: dict[str, float] = {}
        if todo:
            biggest = max(todo, key=lambda n: expected[n]["size"])
            for src, url in source_urls(spec, revision, biggest).items():
                speeds[src] = round(probe(url, args.probe_seconds), 1)
            order = sorted(speeds, key=speeds.get, reverse=True)
            print(f"{key}: probe MB/s {speeds} -> {order}", flush=True)
            if speeds[order[0]] < MIN_OK_MBPS:
                print(f"{key}: WARNING best source below {MIN_OK_MBPS} MB/s", flush=True)

        entry = manifest.get(key, {})
        files = entry.get("files", {})
        for name in expected:
            dest = local / name
            if name not in todo:
                files.setdefault(name, {**expected[name], "source": "existing"})
                continue
            for src in order:
                url = source_urls(spec, revision, name)[src]
                t0 = time.monotonic()
                try:
                    download(url, dest)
                except subprocess.CalledProcessError:
                    print(f"{key}/{name}: {src} failed", flush=True)
                    continue
                if verify(dest, expected[name]):
                    mbps = expected[name]["size"] / (time.monotonic() - t0) / 2**20
                    print(f"{key}/{name}: ok from {src} ({mbps:.1f} MB/s)", flush=True)
                    files[name] = {**expected[name], "source": src, "url": url}
                    break
                print(f"{key}/{name}: hash mismatch from {src}, discarding", flush=True)
                dest.unlink(missing_ok=True)
            else:
                raise RuntimeError(f"{key}/{name}: no source produced the expected bytes")

        manifest[key] = {"repo": spec.repo, "revision": revision,
                         "modelscope": spec.get("modelscope"), "probe_mbps": speeds,
                         "verified_against": f"HF API {spec.repo}@{revision} (via {HF_ENDPOINT})",
                         "files": files}
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"{key}: {spec.repo}@{revision[:10]} verified ({len(files)} files)", flush=True)
    print("MANIFEST written", flush=True)


if __name__ == "__main__":
    main()
