from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_EXAMPLE_VERDICTS = {
    "linear-invalid.json": "INVALID_INPUT",
    "linear-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "linear-program-refuted.json": "REFUTED_IN_DOMAIN",
    "linear-program-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "modular-abstain.json": "ABSTAIN_OUT_OF_DOMAIN",
    "modular-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "polynomial-refuted.json": "REFUTED_IN_DOMAIN",
    "polynomial-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
}
CONFORMANCE_FORMAT = "ECV_CONFORMANCE_V1"
CONFORMANCE_ARCHIVE = f"{CONFORMANCE_FORMAT}.zip"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _conformance_path(root: Path, relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError(f"invalid conformance {field} path")
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if candidate == resolved_root or resolved_root not in candidate.parents:
        raise ValueError(f"conformance {field} escapes its root")
    if not candidate.is_file() or candidate.is_symlink():
        raise ValueError(f"conformance {field} is not a regular file")
    return candidate


def _validate_conformance(root: Path) -> tuple[Path, dict[str, object]]:
    manifest = root / f"{CONFORMANCE_FORMAT}.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError(f"conformance_dir must contain {manifest.name}")
    try:
        document = json.loads(manifest.read_text(encoding="ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("conformance manifest must be valid ASCII JSON") from error
    if not isinstance(document, dict) or document.get("format") != CONFORMANCE_FORMAT:
        raise ValueError("unexpected conformance manifest format")
    if document.get("specs") != ["ECV/1", "ECV/2"]:
        raise ValueError("conformance manifest must declare ECV/1 and ECV/2")
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("conformance manifest must contain cases")
    seen_ids: set[str] = set()
    expected_fields = {
        "expected_exit",
        "expected_result",
        "expected_result_sha256",
        "expected_verdict",
        "id",
        "input",
        "input_sha256",
    }
    for case in cases:
        if not isinstance(case, dict) or set(case) != expected_fields:
            raise ValueError("invalid conformance case shape")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen_ids:
            raise ValueError("conformance case IDs must be nonempty and unique")
        seen_ids.add(case_id)
        for path_field, digest_field in (
            ("input", "input_sha256"),
            ("expected_result", "expected_result_sha256"),
        ):
            path = _conformance_path(root, case[path_field], path_field)
            if _sha256(path) != case[digest_field]:
                raise ValueError(f"conformance hash mismatch: {case_id} {path_field}")
    return manifest, document


def _build_conformance_archive(root: Path, target: Path) -> None:
    files = sorted(
        (path for path in root.rglob("*") if path.is_file() and not path.is_symlink()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    with zipfile.ZipFile(target, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for source in files:
            relative = source.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f"conformance/{relative}", date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def build_release_metadata(
    dist_dir: Path,
    examples_dir: Path,
    conformance_dir: Path,
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

    conformance_manifest, conformance_document = _validate_conformance(conformance_dir)

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

    conformance_archive = output_dir / CONFORMANCE_ARCHIVE
    _build_conformance_archive(conformance_dir, conformance_archive)
    copied.append(conformance_archive)

    example_records = [
        {
            "expected_verdict": EXPECTED_EXAMPLE_VERDICTS[path.name],
            "name": path.name,
            "sha256": _sha256(path),
            "size": path.stat().st_size,
        }
        for path in examples
    ]
    statement = output_dir / "ECV_RELEASE_STATEMENT_V2.json"
    statement.write_text(
        json.dumps(
            {
                "artifacts": artifacts,
                "commit": commit,
                "conformance": {
                    "archive": conformance_archive.name,
                    "archive_sha256": _sha256(conformance_archive),
                    "archive_size": conformance_archive.stat().st_size,
                    "cases": len(conformance_document["cases"]),
                    "format": CONFORMANCE_FORMAT,
                    "manifest_sha256": _sha256(conformance_manifest),
                },
                "contracts": ["ECV/1", "ECV/2"],
                "examples": example_records,
                "format": "ECV_RELEASE_STATEMENT_V2",
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
    parser.add_argument("--conformance-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    arguments = parser.parse_args()
    statement, checksums = build_release_metadata(
        arguments.dist_dir,
        arguments.examples_dir,
        arguments.conformance_dir,
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
