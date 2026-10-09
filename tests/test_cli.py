"""Tests for the CLI: argument parsing defaults/guards, then main() wiring."""

from __future__ import annotations

import csv
import io
import json

import pytest

from golemorph.cli import build_parser
from golemorph.models import Gender


# --- build_parser: defaults and option wiring -------------------------------


def test_defaults_are_usa_single_bare_name():
    """With no argv, the CLI defaults to one American persona, names only."""
    args = build_parser().parse_args([])
    assert args.origin == "USA"
    assert args.count == 1
    assert args.unique is None  # names may repeat unless --unique is set
    assert args.gender is None  # mixed, per-name gender unless forced
    assert args.unweighted is False
    assert args.seed is None
    assert args.format == "name"
    assert args.output is None
    assert args.list_origins is None  # None when the flag is not passed; bare flag yields "all"


def test_origin_accepts_long_and_short_flags():
    parser = build_parser()
    assert parser.parse_args(["--origin", "RUS"]).origin == "RUS"
    assert parser.parse_args(["-o", "chn"]).origin == "CHN"  # upper-cased on parse


def test_gender_choices_map_onto_gender_enum():
    """The -g choices must stay in sync with Gender's values."""
    parser = build_parser()
    for value in ("Male", "Female"):
        assert Gender(parser.parse_args(["-g", value]).gender) is Gender(value)
    with pytest.raises(SystemExit):
        parser.parse_args(["-g", "Other"])


def test_format_choices_cover_every_export():
    parser = build_parser()
    for fmt in ("name", "csv", "json", "gophish"):
        assert parser.parse_args(["-f", fmt]).format == fmt


def test_flags_plumb_seed_unique_count_and_output():
    args = build_parser().parse_args(
        ["-n", "50", "-u", "--seed", "42", "--output", "out.csv", "-f", "csv"]
    )
    assert (args.count, args.unique, args.seed, args.output, args.format) == (
        50,
        "full",  # bare --unique defaults to the whole name
        42,
        "out.csv",
        "csv",
    )
    assert build_parser().parse_args(["--unweighted"]).unweighted is True
    assert build_parser().parse_args(["--list-origins"]).list_origins == "all"
    assert build_parser().parse_args(["--list-origins", "EUROPE"]).list_origins == "europe"


def test_unique_takes_an_optional_part_and_rejects_others():
    parse = build_parser().parse_args
    assert parse(["-u", "first"]).unique == "first"
    assert parse(["--unique", "last"]).unique == "last"
    assert parse(["--unique"]).unique == "full"
    with pytest.raises(SystemExit):
        parse(["--unique", "middle"])  # not a valid part


# --- main(): dispatch and output formats ------------------------------------


def test_list_origins_prints_every_locale_and_exits(capsys):
    from golemorph.cli import main
    from golemorph.loader import load_manifest

    main(["--list-origins"])
    out = capsys.readouterr().out

    # Parse the rich box table: split each row on the vertical rule and keep
    # the data rows. Columns are LABEL, CODE, LANG, DIAL; code is column 1.
    codes = {}
    for line in out.splitlines():
        if "│" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("│").split("│")]
        code = cells[1] if len(cells) > 1 else ""
        if len(code) == 3 and code.isalpha() and code.isupper():
            codes[code] = cells

    assert set(codes) == set(load_manifest())
    assert len(codes) == 45
    fra = codes["FRA"]
    assert fra[0] == "French" and fra[2] == "fr" and fra[3] == "+33"


def _origin_codes(out: str) -> set[str]:
    """Pull the 3-letter codes (column 1) out of a rendered origins listing."""
    found = set()
    for line in out.splitlines():
        if "│" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("│").split("│")]
        code = cells[1] if len(cells) > 1 else ""
        if len(code) == 3 and code.isalpha() and code.isupper():
            found.add(code)
    return found


def test_list_origins_filters_by_group(capsys):
    from golemorph.cli import main

    main(["--list-origins", "asia"])
    codes = _origin_codes(capsys.readouterr().out)
    assert codes == {"CHN", "IDN", "IND", "JPN", "KOR", "MYS", "PHL", "SGP"}


def test_list_origins_group_is_case_insensitive(capsys):
    from golemorph.cli import main

    main(["--list-origins", "AMERICAS"])
    codes = _origin_codes(capsys.readouterr().out)
    assert codes == {"ARG", "BRA", "CAN", "COL", "MEX", "USA"}


def test_list_origins_rejects_unknown_group(capsys):
    from golemorph.cli import main

    with pytest.raises(SystemExit):
        main(["--list-origins", "narnia"])


def test_main_writes_bare_names_to_stdout(capsys):
    from golemorph.cli import main

    main(["-o", "CHN", "--seed", "1"])
    assert capsys.readouterr().out.strip()  # one family-first name, not a record


def test_main_json_output_is_one_full_record(capsys):
    from golemorph.cli import main

    main(["-o", "RUS", "--seed", "7", "-f", "json", "-g", "Female"])
    (record,) = json.loads(capsys.readouterr().out)
    assert record["gender"] == "Female"
    assert record["origin_label"] == "Russian"
    assert "@" in record["email"]


def test_main_gophish_csv_to_file(tmp_path):
    from golemorph.cli import main

    out = tmp_path / "targets.csv"
    main(["-o", "FRA", "-n", "2", "--seed", "3", "-f", "gophish",
          "--output", str(out)])
    with out.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == ["First Name", "Last Name", "Email", "Position"]
    assert len(rows) == 2
    assert rows[0]["Position"]  # Position carries the persona's role


# --- main(): known failures exit cleanly, no traceback ----------------------


def test_unknown_origin_exits_with_clean_message(capsys):
    from golemorph.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["-o", "XYZ"])
    assert "golemorph: error:" in str(exc.value)
    assert "unknown origin" in str(exc.value)


def test_unique_pool_too_small_exits_with_clean_message():
    from golemorph.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["-o", "KOR", "-n", "100000", "--unique", "first"])
    assert "golemorph: error:" in str(exc.value)
    assert "cannot draw" in str(exc.value)
