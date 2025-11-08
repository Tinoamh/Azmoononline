#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main():
    # Ensure inner project package (Azmoononline) is on sys.path when running from repo root
    project_inner = Path(__file__).resolve().parent / 'Azmoononline'
    if project_inner.exists():
        sys.path.insert(0, str(project_inner))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oes.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed and available on your PYTHONPATH."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()