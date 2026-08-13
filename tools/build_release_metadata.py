from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_EXAMPLE_VERDICTS = {
    "linear-invalid.json": "INVALID_INPUT",
    "linear-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "modular-abstain.json": "ABSTAIN_OUT_OF_DOMAIN",
    "modular-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "polynomial-refuted.json": "REFUTED_IN_DOMAIN",
    "polynomial-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_metadata(
    dist_dir: Path,
    examples_dir: Path,
    output_dir: Path,
    *,
    version: str,
    tag: str,
    commit: str,
) -> tuple[Path, Path]:
    if tag != f"v{version}":
        raise ValueError(f"release tag {tag!r} does not match version {version!r}")
    if not COMMIT_PATTERN.fullmatch(commit):
        raise ValueError("commit must be a 40-character lowercase hexadecimal SHA")

    distributions = sorted([*dist_dir.glob("*.whl"), *dist_dir.glob("*.tar.gz")])
    wheels = [path for path in distributions if path.suffix == ".whl"]
    sdists = [path for path in distributions if path.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("dist_dir must contain exactly one wheel and one source distribution")
    expected_names = {
        f"exact_claim_verifier-{version}-py3-none-any.whl",
        f"exact_claim_verifier-{version}.tar.gz",
    }
    if {path.name for path in distributions} != expected_names:
        raise ValueError("distribution filenames do not match the declared ECV version")

    examples = sorted(path for path in examples_dir.glob("*.json") if path.is_file())
    example_names = {path.name for path in examples}
    missing_examples = sorted(EXPECTED_EXAMPLE_VERDICTS.keys() - example_names)
    if missing_examples:
        raise ValueError(f"examples_dir is missing required example: {missing_examples[0]}")
    unexpected_examples = sorted(example_names - EXPECTED_EXAMPLE_VERDICTS.keys())
    if unexpected_examples:
        raise ValueError(f"examples_dir contains unexpected example: {unexpected_examples[0]}")

    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("output_dir must be absent or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, str | int]] = []
    copied: list[Path] = []
    for source in distributions:
        target = output_dir / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        artifacts.append(
            {
                "name": target.name,
                "sha256": _sha256(target),
                "size": target.stat().st_size,
            }
        )
        copied.append(target)

    example_records = [
        {
            "expected_verdict": EXPECTED_EXAMPLE_VERDICTS[path.name],
            "name": path.name,
            "sha256": _sha256(path),
            "size": path.stat().st_size,
        }
        for path in examples
    ]
    statement = output_dir / "ECV_RELEASE_STATEMENT_V1.json"
    statement.write_text(
        json.dumps(
            {
                "artifacts": artifacts,
                "commit": commit,
                "contract": "ECV/1",
                "examples": example_records,
                "format": "ECV_RELEASE_STATEMENT_V1",
                "tag": tag,
                "version": version,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="ascii",
        newline="\n",
    )

    checksums = output_dir / "SHA256SUMS.txt"
    subjects = sorted([*copied, statement], key=lambda path: path.name)
    checksums.write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in subjects),
        encoding="ascii",
        newline="\n",
    )
    return statement, checksums


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic ECV release metadata.")
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--examples-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    arguments = parser.parse_args()
    statement, checksums = build_release_metadata(
        arguments.dist_dir,
        arguments.examples_dir,
        arguments.output_dir,
        version=arguments.version,
        tag=arguments.tag,
        commit=arguments.commit,
    )
    print(statement)
    print(checksums)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
