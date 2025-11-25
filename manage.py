#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main():
    base_dir = Path(__file__).resolve().parent
    inner = base_dir / "Azmoononline"
    # Ensure inner package is discoverable for 'oes.settings'
    if inner.exists():
        sys.path.insert(0, str(inner))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oes.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()