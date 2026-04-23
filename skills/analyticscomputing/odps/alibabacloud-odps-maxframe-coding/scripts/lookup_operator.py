#!/usr/bin/env python3
# /// script
# requires-python = ">=3.7"
# dependencies = []
# ///
"""
MaxFrame API Documentation Query Tool

This script reads Sphinx Markdown output to provide structured API documentation
for use in agent skills and context control.

Features:
- Directly reads Markdown files from `make markdown` output
- Zero complex parsing - Markdown is already structured and LLM-friendly
- Fuzzy search: Supports glob patterns and content search
- Section extraction: Get specific sections (params, examples, etc.)

Usage:
    python lookup_operator.py search <pattern>          # Search names + content (default)
    python lookup_operator.py search <pattern> -n       # Search names only
    python lookup_operator.py search <pattern> --fold   # Fold output to save tokens
    python lookup_operator.py info <name>               # Get full markdown content
    python lookup_operator.py list                      # List all operators
    python lookup_operator.py list --fold               # Fold output to save tokens

Prerequisites:
    Run `make markdown` in the docs directory first.

Sections available:
- signature, description, params/parameters, returns, return_type
- see_also, notes, examples, warnings, references
"""

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Default path to Markdown build output
DEFAULT_MD_DIR = Path(__file__).parent.parent / "references" / "maxframe-client-docs" / "reference"


class APIDocParser:
    """Parser for Sphinx Markdown output files."""

    def __init__(self, md_dir: Path = DEFAULT_MD_DIR):
        self.md_dir = md_dir
        self._index: Optional[Dict[str, Path]] = None

    def _build_index(self) -> Dict[str, Path]:
        """Build an index of operator names to their Markdown file paths."""
        if self._index is not None:
            return self._index

        self._index = {}
        if not self.md_dir.exists():
            return self._index

        # Walk through all .md files
        for md_path in self.md_dir.rglob("*.md"):
            name = md_path.stem  # Remove .md extension
            # Only index API entries (those with qualified names like maxframe.xxx)
            if name.startswith("maxframe.") and "." in name:
                self._index[name] = md_path

        return self._index

    def list_all(self, compact: bool = False) -> List[str]:
        """
        List all available operator names.

        Args:
            compact: If True, return tree-like format with common prefixes folded
        """
        names = sorted(self._build_index().keys())
        if not compact:
            return names
        return self._fold_names(names)

    def _fold_names(self, names: List[str]) -> List[str]:
        """Fold names with common prefixes into tree-like format."""
        if not names:
            return []

        result = []
        prev_parts = []

        for name in names:
            parts = name.split(".")

            # Find common prefix length with previous
            common = 0
            for i, (p, prev) in enumerate(zip(parts, prev_parts)):
                if p == prev:
                    common = i + 1
                else:
                    break

            # Output the differing parts
            if common == 0:
                # No common prefix, output full name
                result.append(name)
            else:
                # Indent based on common prefix depth, show only suffix
                suffix = ".".join(parts[common:])
                indent = "  " * common
                result.append(f"{indent}.{suffix}")

            prev_parts = parts

        return result

    def search(self, pattern: str, search_content: bool = False) -> List[str]:
        """
        Search for operators matching a pattern.

        Args:
            pattern: Search pattern (supports glob wildcards)
            search_content: If True, also search in content

        Examples:
            search('apply_chunk')      -> matches '*apply_chunk*'
            search('DataFrame.apply')  -> matches '*DataFrame.apply*'
            search('mf.*')             -> matches '*mf.*'
        """
        index = self._build_index()

        # Normalize pattern for glob matching
        # If pattern has wildcards, we need to be smarter about wrapping
        has_leading_wildcard = pattern.startswith("*")
        has_trailing_wildcard = pattern.endswith("*")

        if "*" in pattern or "?" in pattern or "[" in pattern:
            # Pattern has wildcards - add leading/trailing wildcards if not present
            glob_pattern = pattern
            if not has_leading_wildcard:
                glob_pattern = "*" + glob_pattern
            if not has_trailing_wildcard:
                glob_pattern = glob_pattern + "*"
        else:
            # No wildcards - wrap with wildcards for substring match
            glob_pattern = f"*{pattern}*"

        matches = set()

        # Search by name
        for name in index.keys():
            if fnmatch.fnmatch(name, glob_pattern) or fnmatch.fnmatch(
                name.lower(), glob_pattern.lower()
            ):
                matches.add(name)

        # Search by content if requested
        if search_content:
            pattern_lower = pattern.lower()
            for name, md_path in index.items():
                if name in matches:
                    continue
                try:
                    content = md_path.read_text(encoding="utf-8").lower()
                    if pattern_lower in content:
                        matches.add(name)
                except IOError:
                    continue

        return sorted(matches)

    def _resolve_name(self, name: str) -> str:
        """Resolve a fuzzy name to full qualified name (case-insensitive)."""
        index = self._build_index()

        # Exact match first (case-insensitive)
        name_lower = name.lower()
        for key in index.keys():
            if key.lower() == name_lower:
                return key

        # Try fuzzy search
        matches = self.search(name)

        if len(matches) == 0:
            raise ValueError(f"No operator found matching '{name}'")
        elif len(matches) == 1:
            return matches[0]
        else:
            # Check for exact suffix match
            suffix_matches = [m for m in matches if m.endswith(f".{name}") or m.endswith(name)]
            if len(suffix_matches) == 1:
                return suffix_matches[0]
            raise ValueError(
                f"Multiple operators match '{name}': {matches[:10]}"
                + (f" (and {len(matches) - 10} more)" if len(matches) > 10 else "")
            )

    def get(self, name: str) -> str:
        """Get full markdown content for an operator."""
        full_name = self._resolve_name(name)
        md_path = self._build_index()[full_name]
        return md_path.read_text(encoding="utf-8")

    def get_section(self, name: str, section: str) -> str:
        """
        Get a specific section from the markdown content.

        Args:
            name: Operator name (supports fuzzy matching)
            section: Section name (case-insensitive):
                - signature: The function signature line
                - description: Description paragraphs
                - params/parameters: Parameters section
                - returns: Returns section
                - return_type: Return type
                - see_also: See Also section
                - notes: Notes section
                - examples: Examples section
                - warnings: Warnings section
                - references: References section

        Returns:
            The section content as string, or empty string if not found.
        """
        content = self.get(name)
        section = section.lower()

        # Section name aliases
        aliases = {
            "params": "parameters",
            "param": "parameters",
            "return": "returns",
            "seealso": "see_also",
            "see also": "see_also",
            "example": "examples",
            "note": "notes",
            "warning": "warnings",
            "reference": "references",
        }
        section = aliases.get(section, section)

        lines = content.split("\n")

        # Special case: signature (first #### line after title)
        if section == "signature":
            for line in lines:
                if line.startswith("#### ") and "(" in line:
                    return line[5:].strip()  # Remove "#### " prefix
            return ""

        # Special case: description (text between title and signature)
        if section == "description":
            desc_lines = []
            after_title = False
            for line in lines:
                # Skip title
                if line.startswith("# "):
                    after_title = True
                    continue
                # Stop at signature
                if line.startswith("#### ") and "(" in line:
                    break
                # Stop at section markers
                if line.startswith("* **") or line.startswith("### "):
                    break
                # Collect description after title
                if after_title and line.strip():
                    desc_lines.append(line)
            return "\n".join(desc_lines).strip()

        # Parameters section (special format: * **Parameters:** followed by list)
        if section == "parameters":
            return self._extract_list_section(lines, "Parameters")

        # Returns section
        if section == "returns":
            return self._extract_inline_section(lines, "Returns")

        # Return type section
        if section == "return_type":
            return self._extract_inline_section(lines, "Return type")

        # Standard header sections (### or #### followed by section name)
        section_map = {
            "see_also": ["SEE ALSO", "See Also"],
            "notes": ["Notes", "Note"],
            "examples": ["Examples", "Example"],
            "warnings": ["Warnings", "Warning"],
            "references": ["References", "Reference"],
        }

        headers = section_map.get(section, [section.title()])
        return self._extract_header_section(lines, headers)

    def _extract_list_section(self, lines: List[str], section_name: str) -> str:
        """Extract a list section like Parameters."""
        result = []
        in_section = False

        for i, line in enumerate(lines):
            if f"**{section_name}:**" in line:
                in_section = True
                # Include the rest of this line if there's content after :**
                continue
            elif in_section:
                # Stop at next top-level section
                if line.startswith("* **") and ":" in line and not line.startswith("  "):
                    # Check if this is a new section (Returns:, Return type:, etc.)
                    if any(s in line for s in ["Returns:", "Return type:", "Raises:", "Yields:"]):
                        break
                result.append(line)

        return "\n".join(result).strip()

    def _extract_inline_section(self, lines: List[str], section_name: str) -> str:
        """Extract an inline section like Returns or Return type."""
        result = []
        in_section = False

        for i, line in enumerate(lines):
            if f"**{section_name}:**" in line:
                in_section = True
                # Check if there's content on the same line after :**
                match = re.search(rf"\*\*{section_name}:\*\*\s*(.*)", line)
                if match and match.group(1).strip():
                    result.append(match.group(1).strip())
                continue
            elif in_section:
                # Stop at next top-level section marker
                if line.startswith("* **") and ":" in line and not line.startswith("  "):
                    break
                # Stop at header
                if line.startswith("### ") or line.startswith("#### "):
                    break
                # Collect content (typically indented on next lines)
                if line.strip():
                    result.append(line.strip())

        return "\n".join(result).strip()

    def _extract_header_section(self, lines: List[str], headers: List[str]) -> str:
        """Extract a section that starts with a header."""
        result = []
        in_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check for section start
            if not in_section:
                for header in headers:
                    if stripped in [f"### {header}", f"#### {header}", f"# {header}", header]:
                        in_section = True
                        break
                continue  # Don't include the header line itself

            if in_section:
                # Stop at next header section (### or #### that doesn't contain function signature)
                if stripped.startswith("### ") or stripped.startswith("#### "):
                    # But don't stop at code block headers
                    if "(" not in stripped and not stripped.startswith("```"):
                        break
                result.append(line)

        return "\n".join(result).strip()

    def get_info(self, name: str) -> Dict[str, str]:
        """
        Get structured info as a dictionary.

        Returns dict with keys: name, signature, description, params, returns,
        return_type, see_also, notes, examples (only non-empty sections included).
        """
        full_name = self._resolve_name(name)
        result = {"name": full_name}

        sections = [
            "signature",
            "description",
            "params",
            "returns",
            "return_type",
            "see_also",
            "notes",
            "examples",
        ]

        for section in sections:
            content = self.get_section(name, section)
            if content:
                result[section] = content

        return result


def main():
    parser = argparse.ArgumentParser(
        description="MaxFrame API Documentation Query Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--md-dir",
        type=Path,
        default=DEFAULT_MD_DIR,
        help="Path to Sphinx Markdown build output directory (default: references/maxframe-client-docs/reference)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all available operators")
    list_parser.add_argument(
        "--md-dir",
        type=Path,
        default=DEFAULT_MD_DIR,
        help="Path to Sphinx Markdown build output directory",
    )
    list_parser.add_argument(
        "--fold",
        action="store_true",
        help="Fold common prefixes to save tokens",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON array",
    )

    # search command
    search_parser = subparsers.add_parser("search", help="Search for operators by pattern")
    search_parser.add_argument(
        "--md-dir",
        type=Path,
        default=DEFAULT_MD_DIR,
        help="Path to Sphinx Markdown build output directory",
    )
    search_parser.add_argument("pattern", help="Search pattern (supports glob wildcards)")
    search_parser.add_argument(
        "-n",
        "--name-only",
        action="store_true",
        help="Search only in names (default: search both names and content)",
    )
    search_parser.add_argument(
        "--fold",
        action="store_true",
        help="Fold common prefixes to save tokens",
    )
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON array",
    )

    # info command
    info_parser = subparsers.add_parser("info", help="Get documentation for an operator")
    info_parser.add_argument(
        "--md-dir",
        type=Path,
        default=DEFAULT_MD_DIR,
        help="Path to Sphinx Markdown build output directory",
    )
    info_parser.add_argument(
        "name", help="Operator name (supports fuzzy matching, case-insensitive)"
    )
    info_parser.add_argument(
        "-s",
        "--section",
        help="Get specific section (signature, description, params, returns, examples, notes, see_also)",
    )
    info_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (only with --section or for structured info)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get md_dir from either the main parser or subparser
    md_dir = getattr(args, "md_dir", DEFAULT_MD_DIR)
    doc_parser = APIDocParser(md_dir)

    try:
        if args.command == "list":
            if args.json:
                operators = doc_parser.list_all(compact=False)
                print(json.dumps(operators))
            else:
                operators = doc_parser.list_all(compact=args.fold)
                print("\n".join(operators))

        elif args.command == "search":
            # Default: search both names and content
            search_content = not args.name_only
            results = doc_parser.search(args.pattern, search_content=search_content)
            if args.json:
                print(json.dumps(results))
            elif args.fold:
                folded = doc_parser._fold_names(results)
                print("\n".join(folded))
            else:
                print("\n".join(results))

        elif args.command == "info":
            if args.section:
                content = doc_parser.get_section(args.name, args.section)
                if args.json:
                    print(json.dumps({args.section: content}, indent=2, ensure_ascii=False))
                else:
                    print(content)
            elif args.json:
                info = doc_parser.get_info(args.name)
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                content = doc_parser.get(args.name)
                print(content)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Markdown directory not found: {args.md_dir}", file=sys.stderr)
        print("Run 'make markdown' in the docs directory first.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
