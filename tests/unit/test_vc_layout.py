# tests/unit/test_vc_layout.py
"""Regression tests for Virtual Console widget layout in the QLC+ export.

QLC+ VC child-widget coordinates are relative to their parent frame, so
overlap is checked per container among its direct children (in the container's
local coordinate space). These tests pin the fix for group-control frames
colliding with the right-column Master frame / SpeedDial: a vertical-overflow
re-pack used to expand group frames to the full screen width, driving them into
the reserved right column. See utils/to_xml/virtual_console_to_xml.py.
"""
import os
import xml.etree.ElementTree as ET

import pytest

from config.models import Configuration
from utils.create_workspace import create_qlc_workspace

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RIGS_DIR = os.path.join(REPO_ROOT, "demos", "rigs")
WORKSPACE_OUT = os.path.join(REPO_ROOT, "workspace.qxw")

RIG_NAMES = [
    "club_band",
    "band_midsize",
    "festival_mainstage",
    "dj_edm",
    "theatre_static",
]

# Full-featured VC export — exercises group controls, presets, and the
# right-column Master frame + SpeedDial that group frames used to collide with.
VC_OPTIONS = {
    "generate_vc": True,
    "group_controls": True,
    "scene_presets": True,
    "movement_presets": True,
    "show_buttons": True,
    "speed_dial": True,
    "master_presets": True,
    "dark_mode": False,
}

WIDGET_TAGS = {"Frame", "SoloFrame", "Button", "Slider", "XYPad", "SpeedDial", "Label", "Clock"}
CONTAINER_TAGS = {"Frame", "SoloFrame"}


def _rect(el):
    ws = el.find("WindowState")
    if ws is None:
        return None
    return (
        int(ws.get("X", 0)), int(ws.get("Y", 0)),
        int(ws.get("Width", 0)), int(ws.get("Height", 0)),
    )


def _overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = min(ax + aw, bx + bw) - max(ax, bx)
    iy = min(ay + ah, by + bh) - max(ay, by)
    return ix > 0 and iy > 0  # touching edges is allowed


def _label(el):
    return f"{el.tag}(id={el.get('ID', '?')}, cap={el.get('Caption', '')!r})"


def _collect_overlaps(container, path, out):
    children = [c for c in container if c.tag in WIDGET_TAGS]
    rects = [(c, _rect(c)) for c in children if _rect(c) is not None]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            (ei, ri), (ej, rj) = rects[i], rects[j]
            if _overlaps(ri, rj):
                out.append(f"{path} :: {_label(ei)} {ri} <-> {_label(ej)} {rj}")
    for c in children:
        if c.tag in CONTAINER_TAGS:
            _collect_overlaps(c, path + "/" + _label(c), out)


def _export_and_parse(rig_name):
    config = Configuration.load(os.path.join(RIGS_DIR, f"{rig_name}.yaml"))
    try:
        create_qlc_workspace(config, VC_OPTIONS)
        tree = ET.parse(WORKSPACE_OUT)
    finally:
        # create_qlc_workspace writes into the repo root; never leave it behind.
        if os.path.exists(WORKSPACE_OUT):
            os.remove(WORKSPACE_OUT)
    root = tree.getroot()
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


@pytest.mark.parametrize("rig_name", RIG_NAMES)
def test_no_vc_widget_overlaps(rig_name):
    """No two sibling VC widgets may overlap in any exported demo rig."""
    root = _export_and_parse(rig_name)
    vc = root.find("VirtualConsole")
    assert vc is not None, "export produced no VirtualConsole"
    main_frame = vc.find("Frame")
    assert main_frame is not None, "VirtualConsole has no main Frame"

    overlaps = []
    _collect_overlaps(main_frame, "MainFrame", overlaps)
    assert not overlaps, "overlapping VC widgets:\n  " + "\n  ".join(overlaps)


@pytest.mark.parametrize("rig_name", RIG_NAMES)
def test_group_frames_clear_right_column(rig_name):
    """Left-column group frames must not intrude into the right-column band.

    The Master frame / SpeedDial live at the largest X in the main frame; every
    other top-level frame must stay strictly left of where that band begins.
    """
    root = _export_and_parse(rig_name)
    main_frame = root.find("VirtualConsole").find("Frame")
    top = [(c, _rect(c)) for c in main_frame if c.tag in WIDGET_TAGS and _rect(c) is not None]
    if len(top) < 2:
        pytest.skip("not enough top-level widgets to have a right column")

    right_band_x = max(x for _, (x, _y, _w, _h) in top)
    right_widgets = {id(c) for c, (x, *_r) in top if x == right_band_x}
    for c, (x, _y, w, _h) in top:
        if id(c) in right_widgets:
            continue
        assert x + w <= right_band_x, (
            f"{_label(c)} (right edge {x + w}) intrudes into right column at x={right_band_x}"
        )
