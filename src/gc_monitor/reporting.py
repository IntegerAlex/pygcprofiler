"""
Reporting helpers for pygcprofiler
Copyright (C) 2024  Akshat Kotpalliwar

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import gc
import json
import sys
from collections import defaultdict

from .logging import GCLogger


def log_snapshot(logger: GCLogger, json_output: bool, stats_only: bool) -> None:
    """Emit a periodic snapshot of GC counts."""
    if stats_only:
        return

    snapshot = {
        "timestamp": gc.get_stats()[0]["collections"] if gc.get_stats() else None,
        "total_objects": len(gc.get_objects()),
        "generations": {},
    }

    try:
        counts = gc.get_count()
        snapshot["generations"] = {
            "gen0": counts[0] if len(counts) > 0 else 0,
            "gen1": counts[1] if len(counts) > 1 else 0,
            "gen2": counts[2] if len(counts) > 2 else 0,
        }
    except Exception as exc:  # noqa: BLE001
        snapshot["error"] = str(exc)

    if json_output:
        logger._log_message(json.dumps(snapshot, indent=2))  # noqa: SLF001
    else:
        gen_info = " | ".join([f"{k}: {v}" for k, v in snapshot["generations"].items()])
        logger._log_message(f"GMEM SNAPSHOT | Total objects: {snapshot['total_objects']} | {gen_info}")  # noqa: SLF001


def dump_objects(logger: GCLogger, should_dump_objects: bool, dump_garbage: bool) -> None:
    """Dump tracked objects when requested."""
    if not (should_dump_objects or dump_garbage):
        return

    logger._log_message("\n=== GC OBJECT DUMP ===")  # noqa: SLF001
    logger._log_message(f"Total tracked objects: {len(gc.get_objects())}")  # noqa: SLF001

    type_counts = defaultdict(int)
    sample = gc.get_objects()[: min(10_000, len(gc.get_objects()))]
    for obj in sample:
        type_counts[type(obj).__name__] += 1

    logger._log_message("\nTop 10 object types:")  # noqa: SLF001
    for obj_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger._log_message(f"  {obj_type}: {count}")  # noqa: SLF001

    if gc.garbage:
        logger._log_message(f"\nUncollectable objects ({len(gc.garbage)}):")  # noqa: SLF001
        for idx, obj in enumerate(gc.garbage[:5]):
            logger._log_message(f"  [{idx}] {type(obj)}")  # noqa: SLF001
        if len(gc.garbage) > 5:
            logger._log_message(f"  ... and {len(gc.garbage) - 5} more")  # noqa: SLF001


def emit_flamegraph(flame_renderer, logger: GCLogger) -> None:
    """Emit terminal flamegraph output if requested."""
    flame_output = flame_renderer.render_terminal_flamegraph(flame_renderer.start_time)
    if isinstance(flame_output, list):
        for line_info in flame_output:
            if line_info[0] == "colored":
                _, plain_line, colored_line = line_info
                print(colored_line, file=sys.stderr)
                if logger.log_handle:
                    logger.log_handle.write(plain_line + "\n")
                    logger.log_handle.flush()
            else:
                _, plain_line = line_info
                logger._log_message(plain_line)  # noqa: SLF001
    else:
        logger._log_message(flame_output)  # noqa: SLF001

