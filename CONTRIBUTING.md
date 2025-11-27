# Contributing to pygcprofiler

Thank you for your interest in contributing to pygcprofiler! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We're all here to build something useful together.

## Getting Started

### Development Setup

```bash
# Clone the repository
git clone https://github.com/IntegerAlex/pygcprofiler.git
cd pygcprofiler

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gc_monitor --cov-report=html

# Run specific test file
pytest tests/test_cli.py
```

### Code Quality

```bash
# Lint code
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Type checking
mypy src/
```

## Design Principles

**CRITICAL**: Any changes to the monitoring callback MUST maintain zero-runtime-overhead:

### Allowed in `_gc_callback`:

- `time.perf_counter()` calls
- Reading from `info` dict (provided by GC)
- Appending to pre-allocated lists
- Simple arithmetic

### NEVER Allowed in `_gc_callback`:

- Any I/O operations (print, file write, logging)
- `gc.get_objects()` or any object graph scanning
- `gc.collect()`, `gc.freeze()`, `gc.set_threshold()`
- Memory measurement (psutil calls)
- Stack trace extraction
- Creating complex objects (dicts, formatted strings)

All heavy processing MUST happen in `stop_monitoring()` at shutdown.

## Pull Request Process

1. **Fork** the repository and create your branch from `main`
2. **Write tests** for any new functionality
3. **Update documentation** if you're changing behavior
4. **Run the test suite** and ensure all tests pass
5. **Run linters** and fix any issues
6. **Submit a PR** with a clear description of changes

### PR Checklist

- [ ] Tests added/updated for new functionality
- [ ] Documentation updated (README, docstrings)
- [ ] CHANGELOG.md updated (under [Unreleased])
- [ ] All tests passing (`pytest`)
- [ ] Linting passes (`ruff check`)
- [ ] Zero-overhead principles maintained (if touching monitor.py)

## Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code change that neither fixes bug nor adds feature
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(cli): add --sample-rate option for high-throughput apps
fix(monitor): prevent double-stop on KeyboardInterrupt
docs(readme): add uvicorn usage examples
```

## Reporting Issues

### Bug Reports

Include:
1. Python version (`python --version`)
2. OS and version
3. pygcprofiler version (`pip show pygcprofiler`)
4. Minimal reproduction steps
5. Expected vs actual behavior
6. Full error traceback if applicable

### Feature Requests

Include:
1. Use case description
2. Proposed solution (if any)
3. Alternatives considered
4. Impact on zero-overhead principles

## Architecture Overview

```
src/gc_monitor/
├── __main__.py   # CLI entry point (main())
├── cli.py        # Argument parsing
├── codegen.py    # Generates injection code for subprocess
├── monitor.py    # Core GC monitoring (ZERO OVERHEAD)
├── logging.py    # Event logging (shutdown only)
├── stats.py      # Statistics calculation (shutdown only)
├── flamegraph.py # Visualization (shutdown only)
├── memory.py     # Memory utilities
└── prompts.py    # AI prompt generation
```

Key insight: `codegen.py` generates Python code that gets injected into the target process via `python -c`. This code imports and uses `GCMonitor` from `monitor.py`.

## License

By contributing, you agree that your contributions will be licensed under the LGPL-2.1 license.

## Questions?

Open an issue with the "question" label or start a discussion.

