"""Command-line interface: `golemorph --help`.

A small set of options covering what a campaign actually needs: pick an
origin, generate a batch, export (bare names, JSON records, GoPhish CSV).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from contextlib import nullcontext

from .loader import origins
from .models import Gender, Persona
from .persona import generate_personas

class _PaddedParser(argparse.ArgumentParser):
    """ArgumentParser that frames its help text with a blank line above and
    below, matching the spacing of the `--list-origins` listing."""

    def format_help(self) -> str:
        return f"\n{super().format_help()}\n"


def build_parser() -> argparse.ArgumentParser:
    parser = _PaddedParser(
        prog="golemorph",
        description="Generate complete, coherent synthetic personas "
        "(names, emails, phones, backstory) for phishing campaigns.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--origin",
        default="USA",
        type=str.upper,  # codes are upper-case; accept any case on the CLI
        metavar="CODE",
        help="origin code, case-insensitive (see --list-origins)",
    )

    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=1,
        help="number of personas to generate",
    )
    parser.add_argument(
        "-u",
        "--unique",
        nargs="?",
        const="full",
        choices=("first", "last", "full"),
        metavar="PART",
        help="reject and redraw duplicates so names don't repeat; PART is "
        "full (whole name, the default when given bare), first (given names) "
        "or last (surnames); errors if the pool is too small",
    )
    parser.add_argument(
        "-g",
        "--gender",
        choices=["Male", "Female"],
        help="force one gender for every persona (default: mixed, per name)",
    )
    parser.add_argument(
        "--unweighted",
        action="store_true",
        help="uniform name sampling instead of frequency-weighted",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="RNG seed for reproducible campaigns (also seeds --unique redraws, "
        "so retries never silently shift the draw)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("name", "csv", "json", "gophish"),
        default="name",
        help="output format: bare names, full CSV/JSON records, or GoPhish CSV",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="write output to FILE instead of stdout",
    )
    parser.add_argument(
        "--list-origins",
        nargs="?",
        const="all",
        default=None,
        type=str.lower,
        choices=("all", *_GROUP_SLUGS),
        metavar="GROUP",
        help="print available origins and exit; optionally filter by region "
        f"group ({', '.join(_GROUP_SLUGS)}), default all",
    )
    return parser


# Region display order; anything not listed is appended alphabetically after.
_REGION_ORDER = ("Europe", "Americas", "Africa & MENA", "Asia-Pacific")

# CLI slug -> region name, for `--list-origins <group>`. Short, lower-case and
# easy to type; the region names themselves carry spaces and punctuation.
_GROUP_SLUGS = {
    "europe": "Europe",
    "americas": "Americas",
    "africa": "Africa & MENA",
    "asia": "Asia-Pacific",
}


def _print_origins(group: str = "all") -> None:
    """Pretty, color listing of origins for `--list-origins`, one table per
    region. `group` is a slug from :data:`_GROUP_SLUGS`, or ``"all"``.

    `rich.Console` detects the terminal: full color + box when attached to a
    TTY, plain text when piped or redirected (and it honors NO_COLOR), so a
    `golemorph --list-origins | grep` stays clean on its own.
    """
    from rich.console import Console
    from rich.table import Table

    # Bucket origins by region, preserving the loader's alphabetical order
    # within each group.
    groups: dict[str, list] = {}
    for p in origins():
        groups.setdefault(p.region, []).append(p)

    ordered = [r for r in _REGION_ORDER if r in groups]
    ordered += sorted(r for r in groups if r not in _REGION_ORDER)

    if group != "all":
        wanted = _GROUP_SLUGS[group]
        ordered = [r for r in ordered if r == wanted]

    # Fixed per-column widths, computed once across *all* origins, so every
    # region table lines up to the same total width instead of each shrinking
    # to its own group's content.
    headers = ("LABEL", "CODE", "LANG", "DIAL")
    all_rows = [
        (p.label, p.code, p.language, p.dial_code) for p in origins()
    ]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in all_rows))
        for i in range(len(headers))
    ]

    console = Console()
    console.print()  # blank line before the listing
    for i, region in enumerate(ordered):
        if i:
            console.print()  # blank line between tables
        members = groups[region]
        table = Table(
            title=f"{region} ({len(members)})",
            header_style="bold cyan",
            title_style="bold magenta",
            title_justify="left",
        )
        table.add_column("LABEL", style="green", width=widths[0])
        table.add_column("CODE", style="yellow", no_wrap=True, width=widths[1])
        table.add_column("LANG", no_wrap=True, width=widths[2])
        table.add_column("DIAL", style="dim", no_wrap=True, width=widths[3])
        for p in members:
            table.add_row(p.label, p.code, p.language, p.dial_code)
        console.print(table)
    console.print()  # blank line after the listing


def _write(format: str, personas: list[Persona], stream) -> None:
    """Serialize personas in the requested export format."""
    if format == "name":
        # Human-facing default: a rich table with the headline persona fields.
        # (The csv/json/gophish formats stay machine-clean for piping.)
        from rich.console import Console
        from rich.table import Table

        table = Table(header_style="bold cyan")
        table.add_column("NAME", style="bold green")
        table.add_column("AGE", justify="right", no_wrap=True)
        table.add_column("BORN", justify="right", no_wrap=True)
        table.add_column("CITY")
        table.add_column("LANG", no_wrap=True)
        table.add_column("ROLE", style="dim")
        table.add_column("PHONE", no_wrap=True)
        table.add_column("EMAIL", style="cyan")
        table.add_column("COMMON", justify="right", no_wrap=True)
        for p in personas:
            table.add_row(
                p.full_name, str(p.age), str(p.birth_year), p.city,
                p.language, p.role, p.phone, p.email, f"{p.commonality}%",
            )
        console = Console(file=stream)
        console.print()  # blank line before the table
        console.print(table)
        console.print()  # blank line after the table
    elif format == "json":
        json.dump(
            [p.to_dict() for p in personas], stream, ensure_ascii=False, indent=2
        )
        stream.write("\n")
    else:  # csv / gophish: tabular exports keyed by their header row
        rows = [
            p.to_gophish() if format == "gophish" else p.to_dict() for p in personas
        ]
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)



def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.list_origins is not None:
        _print_origins(args.list_origins)
        return
    try:
        personas = generate_personas(
            args.origin,
            args.count,
            Gender(args.gender) if args.gender else None,
            seed=args.seed,
            weighted=not args.unweighted,
            unique=args.unique,
        )
    except ValueError as exc:
        # Known, user-facing failures (unknown origin, pool too small for
        # --unique): a clean one-line message, not a traceback.
        raise SystemExit(f"golemorph: error: {exc}") from None

    try:
        with (
            open(args.output, "w", encoding="utf-8", newline="")
            if args.output
            else nullcontext(sys.stdout)
        ) as stream:
            _write(args.format, personas, stream)
    except OSError as exc:
        raise SystemExit(f"golemorph: error: cannot write output: {exc}") from None


if __name__ == "__main__":
    main()
