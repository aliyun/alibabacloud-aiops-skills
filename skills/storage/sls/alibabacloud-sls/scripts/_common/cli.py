"""Small argument helpers shared by the four existing command entry points."""

import argparse


def add_input(parser, positional=False):
    if positional:
        parser.add_argument("input_path", nargs="?", help="JSON file, or - for stdin")
    parser.add_argument("--input", help="JSON file, or - for stdin")


def resolve_input(parser, args):
    positional = getattr(args, "input_path", None)
    if positional is not None and args.input is not None:
        parser.error("Use either --input or a positional file")
    path = args.input if args.input is not None else positional
    if path is None:
        parser.error(
            "Provide --input FILE"
            if not hasattr(args, "input_path")
            else "Provide --input FILE or a positional file"
        )
    return path


def add_validation_options(parser):
    parser.add_argument("--output", help="Save the JSON report to a file; otherwise stdout")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        default=False,
        help="Exit 1 on warnings as well as errors",
    )
    mode.add_argument("--no-strict", dest="strict", action="store_false", help=argparse.SUPPRESS)
