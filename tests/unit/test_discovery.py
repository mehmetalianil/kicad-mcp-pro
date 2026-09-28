from __future__ import annotations

from pathlib import Path

import pytest

from kicad_mcp.discovery import scan_project_dir


def test_scan_finds_kicad_files(tmp_path: Path) -> None:
    (tmp_path / "board.kicad_pcb").touch()
    (tmp_path / "schematic.kicad_sch").touch()
    (tmp_path / "demo.kicad_pro").touch()
    result = scan_project_dir(tmp_path)
    assert result["pcb"] is not None
    assert result["schematic"] is not None
    assert result["project"] is not None


def test_scan_prefers_canonical_project_over_numbered_duplicate(tmp_path: Path) -> None:
    project_dir = tmp_path / "light-noise-detektor"
    project_dir.mkdir()
    canonical = project_dir / "light-noise-detektor.kicad_pro"
    duplicate = project_dir / "light-noise-detektor 2.kicad_pro"
    duplicate.touch()
    canonical.touch()

    result = scan_project_dir(project_dir)

    assert result["project"] == canonical


def test_scan_prefers_board_matching_project_stem(tmp_path: Path) -> None:
    project_dir = tmp_path / "checkout"
    project_dir.mkdir()
    for name in (
        "mixer.kicad_pro",
        "archive.kicad_pcb",
        "mixer-unrouted.kicad_pcb",
        "mixer.kicad_pcb",
        "mixer.kicad_sch",
    ):
        (project_dir / name).touch()

    result = scan_project_dir(project_dir)

    assert result["project"] == project_dir / "mixer.kicad_pro"
    assert result["pcb"] == project_dir / "mixer.kicad_pcb"


def test_scan_prefers_root_schematic_over_child_sheet(tmp_path: Path) -> None:
    project_dir = tmp_path / "checkout"
    project_dir.mkdir()
    for name in (
        "mixer.kicad_pro",
        "mixer.kicad_pcb",
        "channel_strip.kicad_sch",
        "mixer.kicad_sch",
    ):
        (project_dir / name).touch()

    result = scan_project_dir(project_dir)

    assert result["schematic"] == project_dir / "mixer.kicad_sch"


@pytest.mark.parametrize(
    ("suffix", "key"),
    [
        (".kicad_pro", "project"),
        (".kicad_pcb", "pcb"),
        (".kicad_sch", "schematic"),
    ],
)
def test_scan_ignores_kicad_symlink_escaping_project(tmp_path: Path, suffix: str, key: str) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    if suffix != ".kicad_pro":
        (project_dir / "demo.kicad_pro").touch()
    outside = tmp_path / f"victim{suffix}"
    outside.touch()
    link = project_dir / f"demo{suffix}"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    result = scan_project_dir(project_dir)

    assert result[key] is None


def test_scan_uses_safe_schematic_fallback_when_stem_symlink_escapes_project(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "demo.kicad_pro").touch()
    safe = project_dir / "channel.kicad_sch"
    safe.touch()
    outside = tmp_path / "victim.kicad_sch"
    outside.touch()
    link = project_dir / "demo.kicad_sch"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    result = scan_project_dir(project_dir)

    assert result["schematic"] == safe


def test_scan_allows_symlink_that_resolves_inside_project(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "demo.kicad_pro").touch()
    target = project_dir / "actual.kicad_sch"
    target.touch()
    link = project_dir / "demo.kicad_sch"
    try:
        link.symlink_to(target.name)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    result = scan_project_dir(project_dir)

    assert result["schematic"] == link
