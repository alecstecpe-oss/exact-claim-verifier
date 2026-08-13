from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "build_release_metadata.py"
TOOL_SPEC = importlib.util.spec_from_file_location("ecv_build_release_metadata_v2", TOOL_PATH)
assert TOOL_SPEC is not None and TOOL_SPEC.loader is not None
TOOL_MODULE = importlib.util.module_from_spec(TOOL_SPEC)
TOOL_SPEC.loader.exec_module(TOOL_MODULE)
build_release_metadata = TOOL_MODULE.build_release_metadata


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_v2_binds_both_contracts_and_distributes_conformance(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "exact_claim_verifier-0.2.0-py3-none-any.whl"
    sdist = dist / "exact_claim_verifier-0.2.0.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    output = tmp_path / "release"

    statement_path, checksums_path = build_release_metadata(
        dist,
        ROOT / "examples",
        ROOT / "conformance",
        output,
        version="0.2.0",
        tag="v0.2.0",
        commit="a" * 40,
    )

    archive = output / "ECV_CONFORMANCE_V1.zip"
    assert archive.is_file()
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert names == sorted(names)
        assert "conformance/ECV_CONFORMANCE_V1.json" in names
        assert "conformance/inputs/ecv2-lp-verified.json" in names
        assert "conformance/expected/ecv2-lp-verified.json" in names
        assert all(info.compress_type == zipfile.ZIP_STORED for info in bundle.infolist())
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in bundle.infolist())

    manifest = ROOT / "conformance" / "ECV_CONFORMANCE_V1.json"
    statement = json.loads(statement_path.read_text(encoding="ascii"))
    assert statement["format"] == "ECV_RELEASE_STATEMENT_V2"
    assert statement["contracts"] == ["ECV/1", "ECV/2"]
    assert statement["conformance"] == {
        "archive": archive.name,
        "archive_sha256": _sha256(archive),
        "archive_size": archive.stat().st_size,
        "cases": 9,
        "format": "ECV_CONFORMANCE_V1",
        "manifest_sha256": _sha256(manifest),
    }
    assert {record["name"] for record in statement["examples"]} == {
        path.name for path in (ROOT / "examples").glob("*.json")
    }

    checksum_names = {
        line.split("  ", 1)[1] for line in checksums_path.read_text(encoding="ascii").splitlines()
    }
    assert checksum_names == {
        wheel.name,
        sdist.name,
        archive.name,
        statement_path.name,
    }
