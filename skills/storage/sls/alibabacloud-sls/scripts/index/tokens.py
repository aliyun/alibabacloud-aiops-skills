#!/usr/bin/env python3
"""Print the recommended index token delimiters as a JSON array."""

import argparse
import json


TOKENS = [
    ",",
    " ",
    "'",
    '"',
    ";",
    "\\",
    "$",
    "#",
    "!",
    "=",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    "?",
    "@",
    "&",
    "<",
    ">",
    "/",
    ":",
    "\n",
    "\t",
    "\r",
]


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(TOKENS))


if __name__ == "__main__":
    main()
