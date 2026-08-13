from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
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
    "linear-program-refuted.json",
    "linear-program-valid.json",
    "linear-valid.json",
    "modular-abstain.json",
    "modular-valid.json",
    "polynomial-refuted.json",
    "polynomial-valid.json",
]
EXPECTED_VERDICTS = {
    "linear-invalid.json": "INVALID_INPUT",
    "linear-program-refuted.json": "REFUTED_IN_DOMAIN",
    "linear-program-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "linear-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "modular-abstain.json": "ABSTAIN_OUT_OF_DOMAIN",
    "modular-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
    "polynomial-refuted.json": "REFUTED_IN_DOMAIN",
    "polynomial-valid.json": "EXACTLY_VERIFIED_IN_DOMAIN",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_release_inputs(tmp_path: Path, *, version: str = "0.2.0") -> tuple[Path, Path, Path]:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / f"exact_claim_verifier-{version}-py3-none-any.whl").write_bytes(b"wheel")
    (dist / f"exact_claim_verifier-{version}.tar.gz").write_bytes(b"sdist")
    examples = tmp_path / "examples"
    shutil.copytree(ROOT / "examples", examples)
    conformance = tmp_path / "conformance"
    shutil.copytree(ROOT / "conformance", conformance)
    return dist, examples, conformance


def _build(
    dist: Path,
    examples: Path,
    conformance: Path,
    output: Path,
    *,
    version: str = "0.2.0",
    tag: str = "v0.2.0",
) -> tuple[Path, Path]:
    return build_release_metadata(
        dist,
        examples,
        conformance,
        output,
        version=version,
        tag=tag,
        commit="a" * 40,
    )


def test_release_example_verdicts_match_the_committed_fixtures() -> None:
    assert EXPECTED_EXAMPLE_VERDICTS == EXPECTED_VERDICTS
    for name, expected in EXPECTED_EXAMPLE_VERDICTS.items():
        document = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
        assert verify_document(document)["verdict"] == expected


def test_release_metadata_binds_distributions_commit_examples_and_corpus(tmp_path: Path) -> None:
    dist, examples, conformance = _write_release_inputs(tmp_path)
    release = tmp_path / "release"

    statement_path, checksums_path = _build(dist, examples, conformance, release)

    statement = json.loads(statement_path.read_text(encoding="ascii"))
    assert statement["format"] == "ECV_RELEASE_STATEMENT_V2"
    assert statement["contracts"] == ["ECV/1", "ECV/2"]
    assert statement["commit"] == "a" * 40
    assert statement["tag"] == "v0.2.0"
    assert statement["version"] == "0.2.0"
    assert statement["conformance"]["format"] == "ECV_CONFORMANCE_V1"
    assert statement["conformance"]["cases"] == 9
    assert [record["name"] for record in statement["examples"]] == EXAMPLE_NAMES
    assert [record["expected_verdict"] for record in statement["examples"]] == [
        EXPECTED_VERDICTS[name] for name in EXAMPLE_NAMES
    ]

    checksum_lines = checksums_path.read_text(encoding="ascii").splitlines()
    assert checksum_lines == sorted(checksum_lines, key=lambda line: line.split("  ", 1)[1])
    for line in checksum_lines:
        expected, name = line.split("  ", 1)
        assert "/" not in name and "\\" not in name
        assert _sha256(release / name) == expected


def test_release_metadata_rejects_tag_version_mismatch(tmp_path: Path) -> None:
    dist, examples, conformance = _write_release_inputs(tmp_path)
    with pytest.raises(ValueError, match="does not match version"):
        _build(dist, examples, conformance, tmp_path / "release", tag="v0.2.1")


def test_release_metadata_rejects_distribution_version_mismatch(tmp_path: Path) -> None:
    dist, examples, conformance = _write_release_inputs(tmp_path, version="0.1.1")
    with pytest.raises(ValueError, match="filenames do not match"):
        _build(dist, examples, conformance, tmp_path / "release")


def test_release_metadata_rejects_reused_output_directory(tmp_path: Path) -> None:
    dist, examples, conformance = _write_release_inputs(tmp_path)
    release = tmp_path / "release"
    release.mkdir()
    (release / "stale.txt").write_text("stale\n", encoding="ascii")
    with pytest.raises(ValueError, match="absent or empty"):
        _build(dist, examples, conformance, release)


def test_release_metadata_rejects_incomplete_example_set(tmp_path: Path) -> None:
    dist, examples, conformance = _write_release_inputs(tmp_path)
    (examples / EXAMPLE_NAMES[0]).unlink()
    with pytest.raises(ValueError, match="missing required example"):
        _build(dist, examples, conformance, tmp_path / "release")


def test_release_metadata_rejects_tampered_conformance_vector(tmp_path: Path) -> None:
    dist, examples, conformance = _write_release_inputs(tmp_path)
    vector = conformance / "inputs" / "ecv2-lp-verified.json"
    vector.write_bytes(vector.read_bytes() + b" ")
    with pytest.raises(ValueError, match="conformance hash mismatch"):
        _build(dist, examples, conformance, tmp_path / "release")
