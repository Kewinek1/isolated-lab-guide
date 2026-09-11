#!/usr/bin/env python3
"""Create new private lesson tokens outside the public repository.

Requires POSIX O_NOFOLLOW support. Symlink path components and existing files
are refused. The destination directory must already exist; tokens are not printed.
"""
import argparse
import json
import os
from pathlib import Path
import secrets

PUBLIC_ROOT = Path(__file__).resolve().parents[2]


def open_private_output(path):
    absolute = Path(path).absolute()
    normalized = Path(os.path.abspath(absolute))
    public = PUBLIC_ROOT.resolve()
    if normalized == public or public in normalized.parents:
        raise ValueError("Token output must be outside the public repository")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY") or os.open not in os.supports_dir_fd:
        raise ValueError("Token creation requires POSIX O_NOFOLLOW and directory-relative open support")
    if not absolute.name:
        raise ValueError("A token file path is required")
    directory = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in absolute.parts[1:-1]:
            next_directory = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        return os.open(absolute.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                       0o600, dir_fd=directory)
    finally:
        os.close(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Path outside the public repository")
    args = parser.parse_args(argv)
    try:
        fd = open_private_output(args.output)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            tokens = {"alpha": secrets.token_urlsafe(32), "beta": secrets.token_urlsafe(32)}
            json.dump(tokens, stream, indent=2)
            stream.write("\n")
    except (OSError, ValueError) as error:
        raise SystemExit("Could not create token file: " + str(error)) from None
    print("Created private tokens. Do not commit or publish that file.")


if __name__ == "__main__":
    main()
