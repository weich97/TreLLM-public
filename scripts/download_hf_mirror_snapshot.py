from __future__ import annotations

import argparse
import os
import urllib.error
import urllib.request
from pathlib import Path

BGE_M3_FILES = [
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "sentencepiece.bpe.model",
    "pytorch_model.bin",
    "sparse_linear.pt",
    "1_Pooling/config.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download selected Hugging Face files through a mirror without relying on "
            "huggingface_hub HEAD metadata validation."
        )
    )
    parser.add_argument("repo_id", nargs="?", default="BAAI/bge-m3")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--endpoint", default=os.environ.get("HF_ENDPOINT", "https://hf-mirror.com").rstrip("/"))
    parser.add_argument("--local-dir", default=".tmp/bge-m3-hf")
    parser.add_argument(
        "--include",
        nargs="*",
        default=None,
        help="Files to download. Defaults to the SentenceTransformers files required for BAAI/bge-m3.",
    )
    parser.add_argument("--force", action="store_true", help="Redownload files even if they already exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = args.include if args.include is not None else BGE_M3_FILES
    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    for relative_path in files:
        url = f"{args.endpoint}/{args.repo_id}/resolve/{args.revision}/{relative_path}"
        destination = local_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        download(url, destination, force=args.force)
    print(f"Downloaded {len(files)} files to {local_dir}")
    return 0


def download(url: str, destination: Path, *, force: bool) -> None:
    if destination.exists() and destination.stat().st_size > 0 and not force:
        print(f"skip {destination} ({destination.stat().st_size} bytes)")
        return

    partial = destination.with_suffix(destination.suffix + ".part")
    resume_from = partial.stat().st_size if partial.exists() and not force else 0
    if force and partial.exists():
        partial.unlink()
        resume_from = 0

    headers = {"User-Agent": "TreLLM mirror downloader"}
    if resume_from:
        headers["Range"] = f"bytes={resume_from}-"

    try:
        with open_url(url, headers=headers) as response:
            status = getattr(response, "status", 200)
            mode = "ab" if resume_from and status == 206 else "wb"
            if resume_from and status != 206:
                print(f"restart {destination}; mirror did not honor byte range")
            print(f"download {url} -> {destination}")
            with partial.open(mode) as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while downloading {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while downloading {url}: {exc.reason}") from exc

    partial.replace(destination)


def open_url(url: str, *, headers: dict[str, str], redirects: int = 8):
    current_url = url
    for _ in range(redirects):
        request = urllib.request.Request(current_url, headers=headers)
        try:
            return urllib.request.urlopen(request, timeout=60)
        except urllib.error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise
            location = exc.headers.get("Location")
            if not location:
                raise
            current_url = urllib.request.urljoin(current_url, location)
    raise RuntimeError(f"Too many redirects while downloading {url}")


if __name__ == "__main__":
    raise SystemExit(main())
