# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release preparation

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
- Requires Python 3.12+
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
3. Create git tag: `git tag -s v0.1.0 -m "Release v0.1.0"`
4. Build and publish: `python -m build && twine upload dist/*`

[Unreleased]: https://github.com/AkshatKotpalliwar/pygcprofiler/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AkshatKotpalliwar/pygcprofiler/releases/tag/v0.1.0

