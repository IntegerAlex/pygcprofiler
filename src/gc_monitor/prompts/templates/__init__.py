# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""
Prompt templates organized by category.

Templates are split into:
- headers.py: Application context headers
- issues.py: Issue-specific templates
- solutions.py: Framework-specific solution code
- validation.py: Validation and rollback templates
"""

from .headers import HEADERS
from .issues import ISSUE_TEMPLATES, METRICS_TEMPLATE
from .solutions import SOLUTIONS
from .validation import ROLLBACK_TEMPLATE, VALIDATION_TEMPLATE

__all__ = [
    "HEADERS",
    "ISSUE_TEMPLATES",
    "METRICS_TEMPLATE",
    "SOLUTIONS",
    "ROLLBACK_TEMPLATE",
    "VALIDATION_TEMPLATE",
]

