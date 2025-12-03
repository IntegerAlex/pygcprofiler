# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2025-12-01

### Fixed

- Fixed module mode (`-m`) support to work with flags like `--live`, `--json`, etc. Previously required `--` separator.
- Fixed indentation error in terminal flamegraph handling that caused syntax errors.
- Improved CLI argument parsing to automatically handle `-m` flag without requiring manual `--` separator.

### Added

- Comprehensive CLI flag test suite covering all monitoring options and flag combinations.
- Test for module mode (`-m`) with various flag combinations including `--live`.
- `pygctest` package for testing module-mode functionality.

## [0.4.0] - 2025-12-01

### Changed

- Bumped minimum supported Python version down to 3.10+ (was 3.12+) and updated tooling configuration (`ruff`, `mypy`) accordingly.
- Documented deprecation of programmatic usage (`GCMonitor`, `GCStatistics`, `GCLogger`) and added LSP-visible `deprecated` annotations for these classes.
- Declared `typing-extensions` as a runtime dependency to support the deprecation annotations on all supported Python versions.

## [0.3.6] - 2025-11-29

### Fixed

- Added `enable_prompt` to `GCMonitor.__slots__` to avoid `AttributeError` when using the `--prompt` flag in packaged wheels.
- Ensured the `--prompt` flag is fully wired through config and only generates AI prompts when explicitly enabled.
- Updated workspace configuration for `uv` (`[tool.uv.workspace]`) and refreshed documentation references.

## [0.3.5] - 2025-11-29

### Added

- **Conditional AI prompt generation**:
  - Added `--prompt` flag to control when AI optimization prompts are generated and displayed.
  - Prompts are now hidden by default to keep output clean; use `--prompt` to enable them.
  - Applies to both `pygcprofiler` and `gc-util.py` commands.

### Fixed

- Fixed flag ordering validation to include `--prompt` flag, ensuring it must appear before the script path.
- Updated error message examples to include `--prompt` for clarity.

## [0.3.4] - 2025-11-29

### Changed

- Enforced CLI flag ordering so all monitoring flags (`--live`, `--interval`, `--stats-only`, etc.) must come **before** the script path:
  - `pygcprofiler run --flag --flag test.py [script flags/args...]`
  - `gc-util.py run --flag --flag test.py [script flags/args...]`
- Added clear error messaging when monitoring flags are mistakenly placed after the script/module arguments.

## [0.3.3] - 2025-11-29

### Changed

- Improved CLI UX:
  - Added GNU gdb–style banner (name/author/license) on successful `pygcprofiler run …` and `gc-util.py run …`.
  - When invoked without subcommands, both `pygcprofiler` and `gc-util.py` now print a concise banner plus usage instead of a bare error.
- Cleaned up CLI logging:
  - Stopped printing the full injected `python -c "<monitoring_code>"` command; only a short `GMEM Running: <python> <script> …` line is shown.

## [0.3.0] - 2025-11-28

### Added
- **Real-time dashboard overhaul**:

  - Switched browser transport from WebSockets to **Server-Sent Events (SSE)** for simpler, one-way streaming over HTTP.
  - Added rich, modern dashboard UI split into `index.html`, `css/style.css`, and `js/app.js`.
  - Implemented live scatter-plot visualization with per-generation coloring, rolling 5-minute window, and alert toasts for long pauses.
- **Auto-dashboard for `--live`**:
  - `pygcprofiler run --live …` and `gc-util.py run --live …` now **auto-start** the dashboard process (FastAPI + Uvicorn) pointing at the correct UDP host/port.
  - Best-effort cleanup of the auto-started dashboard on normal exit and on `Ctrl+C`, with hardened termination logic.
- **PromptBuilder for AI optimization**:
  - New `gc_monitor.prompts.PromptBuilder` that builds a comprehensive AI prompt from `GCStatistics` and buffered events.
  - Integrated with `GCMonitor.stop_monitoring()` to emit AI optimization prompts alongside blunder detection and threshold recommendations.
- **Modular long-running dashboard test**:
  - Added `dashboard_long_test.py` to generate sustained GC churn for visually stress-testing the dashboard in non-production environments.

### Changed
- **Refactored core monitoring pipeline for modularity**:
  - Split `monitor.py` into focused modules:
    - `udp_emitter.py` – fire-and-forget UDP emitter for live monitoring.
    - `callback.py` – minimal GC callback factory (`create_gc_callback`).
    - `processing.py` – buffered event processing and final summary/flamegraph output.
    - `utils.py` – snapshot and object-dump utilities with `psutil` fallback.
    - `blunders.py` – GC blunder detection and recommendation generation.
    - `prompts.py` – AI prompt generation (`PromptBuilder`).
  - Kept `GCMonitor` under 300 LOC while preserving zero-overhead design guarantees.
- **CLI and code generation cleanup**:
  - Introduced a dedicated `gc_util/` package:
    - `gc_util.codegen` – monitoring code generation.
    - `gc_util.cli` – argument parsing for `gc-util.py`.
    - `gc_util.main` – entrypoint logic, including auto-dashboard support.
    - `gc_util.templates` – extracted monitoring code template (injected via `python -c`).
  - Reduced `gc-util.py` to a thin wrapper delegating to `gc_util.main:main`.
- **Dashboard server improvements**:
  - `dashboard/server.py` now uses an asyncio-based UDP listener that immediately forwards JSON events to SSE clients via an internal `ConnectionManager`.
  - Added robust logging and error handling around UDP decoding and SSE streaming.

### Fixed
- Ensured `GCMonitor` callback registration/cleanup is robust:
  - Properly tracks `_gc_callback` in `__slots__` and safely removes it from `gc.callbacks` on shutdown.
  - Avoids AttributeErrors in `__del__` when instances are GC’d.
- Hardened dashboard auto-start/cleanup:
  - Prevents auto-start code from masking the underlying script exit status.
  - Best-effort termination of orphaned dashboard processes on `KeyboardInterrupt` during shutdown.

## [0.1.0] - 2024-11-27

### Added

- **Zero-overhead GC monitoring** using `gc.callbacks` mechanism
- **CLI interface** with `pygcprofiler` and `gc-monitor` commands
- **Module mode support** (`-m`) for running uvicorn, gunicorn, etc.
- **ASCII flame graph visualization** with color support
- **JSON output mode** for log aggregation systems
- **Threshold-based alerting** for long GC pauses
- **AI optimization prompts** with actionable recommendations
- **Object type analysis** at shutdown (`--dump-objects`)
- **Uncollectable object detection** (`--dump-garbage`)
- **File logging** with `--log-file` option
- **Configurable duration buckets** for pause categorization

### Design Principles
- Callback only records timestamps and counters (no I/O during GC)
- Uses `time.perf_counter()` for high-precision timing
- All output buffered until shutdown
- Never calls `gc.get_objects()`, `gc.collect()`, `gc.freeze()`, or `gc.set_threshold()`
- No background threads introduced

### Technical Details
- Requires Python 3.10+
- Depends on `psutil` for memory measurement (optional, graceful fallback)
- Events stored as lightweight tuples to minimize object creation
- Lazy initialization of logging/stats components

## Version History

### Versioning Policy

- **MAJOR**: Breaking changes to CLI interface or public API
- **MINOR**: New features, non-breaking enhancements
- **PATCH**: Bug fixes, documentation updates

### Release Process

1. Update version in `pyproject.toml` and `src/gc_monitor/__init__.py`
2. Update this CHANGELOG with release date
3. Create git tag: `git tag -s vX.Y.Z -m "Release vX.Y.Z"`
4. Build and publish: `python -m build && twine upload dist/*`

