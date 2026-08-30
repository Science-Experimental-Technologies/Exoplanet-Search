import json
from xml.etree import ElementTree

from scripts.build_cli_previews import compact_plan, normalize_plan, render_terminal


def test_plan_normalization_preserves_every_non_timestamp_field():
    source = {"started_at_utc": "one", "finished_at_utc": "two", "status": "dry_run",
              "stages": [{"stage": 0, "status": "would_run"}], "options": {"dry_run": True}}
    result = normalize_plan(json.dumps(source))
    assert result == {key: value for key, value in source.items() if not key.endswith("_at_utc")}


def test_compact_preview_preserves_exact_stage_values():
    plan = {"status": "dry_run", "config_path": "configs/base.yaml",
            "stages": [{"stage": 0, "name": "environment", "status": "would_run"}],
            "options": {"dry_run": True}}
    assert json.loads(compact_plan(plan)) == {key: plan[key] for key in ("status", "config_path", "stages")}


def test_terminal_svg_escapes_cli_text_and_grows_for_long_lines():
    svg = render_terminal("CLI <preview>", "python --help", "<command> & options\n" + "x" * 120, "stdout only")
    root = ElementTree.fromstring(svg)
    assert int(root.attrib["width"]) >= 80 + 120 * 12
    assert "<command> & options" in "".join(root.itertext())
