#!/usr/bin/env python3
"""CLI script to seed incident knowledge base from URLs or JSONL files.

Usage:
    python seed-knowledge-base.py --url <post-mortem-url>
    python seed-knowledge-base.py --file incidents.jsonl --auto-approve
    python seed-knowledge-base.py --file incidents.jsonl --dry-run

Flags:
    --url <url>:      Ingest single incident from URL (extract metadata via LLM)
    --file <path>:    Ingest incidents from JSONL file
    --auto-approve:   Skip manual review step
    --dry-run:        Show what would be ingested without persisting
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


async def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Seed incident knowledge base from post-mortems")
    parser.add_argument("--url", type=str, help="Ingest incident from URL")
    parser.add_argument("--file", type=str, help="Ingest incidents from JSONL file")
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip manual review step",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without persisting",
    )

    args = parser.parse_args()

    if not args.url and not args.file:
        parser.print_help()
        return 1

    if args.url:
        return await _ingest_url(args.url, auto_approve=args.auto_approve, dry_run=args.dry_run)
    elif args.file:
        return await _ingest_file(args.file, auto_approve=args.auto_approve, dry_run=args.dry_run)

    return 0


async def _ingest_url(url: str, *, auto_approve: bool = False, dry_run: bool = False) -> int:
    """Ingest incident from URL."""
    print(f"Ingesting from URL: {url}")
    print("Feature not yet implemented: LLM-powered URL extraction")
    return 1


async def _ingest_file(file_path: str, *, auto_approve: bool = False, dry_run: bool = False) -> int:
    """Ingest incidents from JSONL file."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    print(f"Ingesting from file: {file_path}")
    if dry_run:
        print("[DRY RUN] Would ingest the following incidents (no persistence):")

    incident_count = 0
    try:
        with path.open() as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    if dry_run:
                        print(
                            f"  {data.get('title', 'Untitled')} (category: {data.get('category')})"
                        )
                    incident_count += 1
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}", file=sys.stderr)
                    return 1

        if dry_run:
            print(f"\nTotal incidents to ingest: {incident_count}")
        else:
            print("Feature not yet implemented: Persistence layer")

        return 0
    except Exception as e:
        print(f"Error ingesting file: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
