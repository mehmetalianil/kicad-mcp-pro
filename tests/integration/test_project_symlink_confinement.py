from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kicad_mcp.config import reset_config
from kicad_mcp.server import build_server
from tests.conftest import call_tool_text


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.anyio
async def test_auto_selected_schematic_symlink_cannot_read_or_write_outside_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_kicad,
) -> None:
    _ = mock_kicad
    project = tmp_path / "demo"
    project.mkdir()
    (project / "demo.kicad_pro").write_text("{}\n", encoding="utf-8")
    outside = tmp_path / "victim.kicad_sch"
    outside.write_text(
        '(kicad_sch (symbol (property "Reference" "R1") (property "Value" "OUTSIDE_CANARY")))\n',
        encoding="utf-8",
    )
    link = project / "demo.kicad_sch"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    before = _sha256(outside)
    monkeypatch.setenv("KICAD_MCP_OPERATING_MODE", "write")
    monkeypatch.delenv("KICAD_MCP_WORKSPACE_ROOT", raising=False)
    reset_config()
    server = build_server("schematic")

    await call_tool_text(server, "kicad_set_project", {"project_dir": str(project)})
    read_result = await call_tool_text(server, "sch_get_symbols", {})
    write_result = await call_tool_text(
        server,
        "sch_add_label",
        {"name": "SHOULD_NOT_WRITE", "x_mm": 10.0, "y_mm": 10.0, "rotation": 0},
    )

    assert "OUTSIDE_CANARY" not in read_result
    assert "schematic" in read_result.lower()
    assert "schematic" in write_result.lower()
    assert _sha256(outside) == before
    assert link.is_symlink()


@pytest.mark.anyio
async def test_auto_selected_schematic_symlink_cannot_write_valid_design_outside_project(
    tmp_path: Path,
    sample_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_kicad,
) -> None:
    _ = mock_kicad
    project = tmp_path / "malicious"
    project.mkdir()
    (project / "malicious.kicad_pro").write_text("{}\n", encoding="utf-8")
    outside = tmp_path / "victim-valid.kicad_sch"
    outside.write_bytes((sample_project / "demo.kicad_sch").read_bytes())
    link = project / "malicious.kicad_sch"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    before = _sha256(outside)
    monkeypatch.setenv("KICAD_MCP_OPERATING_MODE", "write")
    monkeypatch.delenv("KICAD_MCP_WORKSPACE_ROOT", raising=False)
    reset_config()
    server = build_server("schematic")

    await call_tool_text(server, "kicad_set_project", {"project_dir": str(project)})
    write_result = await call_tool_text(
        server,
        "sch_add_label",
        {"name": "SHOULD_NOT_WRITE", "x_mm": 10.0, "y_mm": 10.0, "rotation": 0},
    )

    assert "schematic" in write_result.lower()
    assert _sha256(outside) == before
    assert link.is_symlink()
