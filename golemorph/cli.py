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

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
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
        action="store_true",
        help="print available origins with their metadata and exit",
    )
    return parser


def _write(format: str, personas: list[Persona], stream) -> None:
    """Serialize personas in the requested export format."""
    if format == "name":
        # Bare names, handy for one-liners and diffs.
        stream.write("\n".join(p.full_name for p in personas) + "\n")
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
    if args.list_origins:
        for profile in origins():
            # The dial code is resolved into the template so the listing shows
            # the number the caller actually gets ("tel=+33 6 …"), not "{d}".
            # Only {d} is filled: {p}/{gN} stay as placeholders to be drawn per persona.
            phone = profile.phone_format.replace("{d}", profile.dial_code)
            print(
                f"{profile.code}\t{profile.label}\t"
                f"lang={profile.language} order={profile.name_order} "
                f"tel={phone}"
            )
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
