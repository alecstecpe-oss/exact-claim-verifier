from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from exact_claim_verifier import verify_document

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "build_release_metadata.py"
TOOL_SPEC = importlib.util.spec_from_file_location("ecv_build_release_metadata", TOOL_PATH)
assert TOOL_SPEC is not None and TOOL_SPEC.loader is not None
TOOL_MODULE = importlib.util.module_from_spec(TOOL_SPEC)
TOOL_SPEC.loader.exec_module(TOOL_MODULE)
EXPECTED_EXAMPLE_VERDICTS = TOOL_MODULE.EXPECTED_EXAMPLE_VERDICTS
build_release_metadata = TOOL_MODULE.build_release_metadata

EXAMPLE_NAMES = [
    "linear-invalid.json",
    "linear-valid.json",
    "modular-abstain.json",
    "modular-valid.json",
    "polynomial-refuted.json",
    "polynomial-valid.json",
]
EXPECTED_VERDICTS = {
    "linear-invalid.json": "INVALID_INPUT",
    "linear-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "modular-abstain.json": "ABSTAIN_OUT_OF_DOMAIN",
    "modular-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "polynomial-refuted.json": "REFUTED_IN_DOMAIN",
    "polynomial-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_release_inputs(tmp_path: Path, *, version: str = "0.1.1") -> tuple[Path, Path]:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / f"exact_claim_verifier-{version}-py3-none-any.whl").write_bytes(b"wheel")
    (dist / f"exact_claim_verifier-{version}.tar.gz").write_bytes(b"sdist")
    examples = tmp_path / "examples"
    examples.mkdir()
    for name in EXAMPLE_NAMES:
        (examples / name).write_text("{}\n", encoding="ascii")
    return dist, examples


def test_release_example_verdicts_match_the_committed_fixtures() -> None:
    assert EXPECTED_EXAMPLE_VERDICTS == EXPECTED_VERDICTS
    for name, expected in EXPECTED_EXAMPLE_VERDICTS.items():
        document = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
        assert verify_document(document)["verdict"] == expected


def test_release_metadata_binds_distributions_commit_and_examples(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "exact_claim_verifier-0.1.1-py3-none-any.whl"
    sdist = dist / "exact_claim_verifier-0.1.1.tar.gz"
    wheel.write_bytes(b"wheel-bytes")
    sdist.write_bytes(b"sdist-bytes")
    examples = tmp_path / "examples"
    examples.mkdir()
    for name in EXAMPLE_NAMES:
        (examples / name).write_text(f'{{"name":"{name}"}}\n', encoding="ascii")
    release = tmp_path / "release"
    commit = "a" * 40

    statement_path, checksums_path = build_release_metadata(
        dist,
        examples,
        release,
        version="0.1.1",
        tag="v0.1.1",
        commit=commit,
    )

    statement = json.loads(statement_path.read_text(encoding="ascii"))
    assert statement == {
        "artifacts": [
            {"name": wheel.name, "sha256": _sha256(wheel), "size": len(b"wheel-bytes")},
            {"name": sdist.name, "sha256": _sha256(sdist), "size": len(b"sdist-bytes")},
        ],
        "commit": commit,
        "contract": "ECV/1",
        "examples": [
            {
                "expected_verdict": EXPECTED_VERDICTS[name],
                "name": name,
                "sha256": _sha256(examples / name),
                "size": (examples / name).stat().st_size,
            }
            for name in EXAMPLE_NAMES
        ],
        "format": "ECV_RELEASE_STATEMENT_V1",
        "tag": "v0.1.1",
        "version": "0.1.1",
    }
    checksum_lines = checksums_path.read_text(encoding="ascii").splitlines()
    assert checksum_lines == sorted(checksum_lines, key=lambda line: line.split("  ", 1)[1])
    assert {line.split("  ", 1)[1] for line in checksum_lines} == {
        wheel.name,
        sdist.name,
        statement_path.name,
    }
    for line in checksum_lines:
        expected, name = line.split("  ", 1)
        assert "/" not in name and "\\" not in name
        assert _sha256(release / name) == expected


def test_release_metadata_rejects_tag_version_mismatch(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "package.whl").write_bytes(b"wheel")
    (dist / "package.tar.gz").write_bytes(b"sdist")
    examples = tmp_path / "examples"
    examples.mkdir()
    for name in EXAMPLE_NAMES:
        (examples / name).write_text("{}\n", encoding="ascii")

    with pytest.raises(ValueError, match="does not match version"):
        build_release_metadata(
            dist,
            examples,
            tmp_path / "release",
            version="0.1.1",
            tag="v0.1.2",
            commit="a" * 40,
        )


def test_release_metadata_rejects_distribution_version_mismatch(tmp_path: Path) -> None:
    dist, examples = _write_release_inputs(tmp_path, version="0.1.0")

    with pytest.raises(ValueError, match="filenames do not match"):
        build_release_metadata(
            dist,
            examples,
            tmp_path / "release",
            version="0.1.1",
            tag="v0.1.1",
            commit="a" * 40,
        )


def test_release_metadata_rejects_reused_output_directory(tmp_path: Path) -> None:
    dist, examples = _write_release_inputs(tmp_path)
    release = tmp_path / "release"
    release.mkdir()
    (release / "stale.txt").write_text("stale\n", encoding="ascii")

    with pytest.raises(ValueError, match="absent or empty"):
        build_release_metadata(
            dist,
            examples,
            release,
            version="0.1.1",
            tag="v0.1.1",
            commit="a" * 40,
        )


def test_release_metadata_rejects_incomplete_example_set(tmp_path: Path) -> None:
    dist, examples = _write_release_inputs(tmp_path)
    (examples / EXAMPLE_NAMES[0]).unlink()

    with pytest.raises(ValueError, match="missing required example"):
        build_release_metadata(
            dist,
            examples,
            tmp_path / "release",
            version="0.1.1",
            tag="v0.1.1",
            commit="a" * 40,
        )
