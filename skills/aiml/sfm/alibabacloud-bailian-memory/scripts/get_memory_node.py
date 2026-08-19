#!/usr/bin/env python3
"""
Get the detail of a single memory fragment by memory_node_id.

Sends REST GET /memory_nodes/{id}.
Use before update/delete to display the target content for confirmation.

Usage:
    python3 scripts/get_memory_node.py --memory-node-id <id>
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_client import MemoryClient, MemoryApiError


def main():
    parser = argparse.ArgumentParser(description="Get a single memory fragment detail.")
    parser.add_argument("--memory-node-id", required=True, help="Memory fragment ID.")
    args = parser.parse_args()

    try:
        client = MemoryClient()
        result = client.get_memory_node(args.memory_node_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except MemoryApiError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
