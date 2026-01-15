#!/usr/bin/env python3
"""
organize_files.py

Organize files in a directory into folders by file format.

Usage:
    python organize_files.py /path/to/dir --recursive --dry-run --verbose

Features:
- Classifies files by extension into categories (images, videos, documents, audio, archives, code, others)
- Creates folders like: Images/.jpg, Documents/.pdf, Code/.py
- Optional recursive traversal
- Dry-run mode to preview changes
- Safe conflict resolution (adds numeric suffix) unless --overwrite is set
"""

from pathlib import Path
import shutil
import argparse
import mimetypes
import sys

# Mapping of extensions (lowercase, without dot) to category names
EXTENSION_CATEGORIES = {
    # Images
    "jpg": "Images", "jpeg": "Images", "png": "Images", "gif": "Images",
    "bmp": "Images", "webp": "Images", "tif": "Images", "tiff": "Images",
    "svg": "Images", "ico": "Images",

    # Videos
    "mp4": "Videos", "mkv": "Videos", "mov": "Videos", "avi": "Videos",
    "wmv": "Videos", "flv": "Videos", "webm": "Videos",

    # Audio
    "mp3": "Audio", "wav": "Audio", "flac": "Audio", "aac": "Audio",
    "ogg": "Audio", "m4a": "Audio",

    # Documents
    "pdf": "Documents", "doc": "Documents", "docx": "Documents",
    "xls": "Documents", "xlsx": "Documents", "ppt": "Documents",
    "pptx": "Documents", "txt": "Documents", "md": "Documents",
    "rtf": "Documents", "odt": "Documents",

    # Archives
    "zip": "Archives", "tar": "Archives", "gz": "Archives", "bz2": "Archives",
    "7z": "Archives", "rar": "Archives",

    # Code
    "py": "Code", "js": "Code", "ts": "Code", "java": "Code", "c": "Code",
    "cpp": "Code", "cs": "Code", "go": "Code", "rb": "Code", "rs": "Code",
    "php": "Code", "html": "Code", "css": "Code", "json": "Code", "xml": "Code",
    "sh": "Code", "ps1": "Code",
}

def guess_category_by_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        if mime.startswith("image/"):
            return "Images"
        if mime.startswith("video/"):
            return "Videos"
        if mime.startswith("audio/"):
            return "Audio"
        if mime in ("application/zip", "application/x-tar"):
            return "Archives"
        if mime in ("application/pdf", "text/plain", "text/html", "application/msword"):
            return "Documents"
    return "Others"

def get_category(path: Path) -> (str, str):
    """
    Return (category, extension_folder_name) for a file Path.
    extension_folder_name is the extension without dot, or 'no_ext' for files without extension.
    """
    if path.suffix:
        ext = path.suffix.lower().lstrip(".")
    else:
        ext = ""

    if ext:
        category = EXTENSION_CATEGORIES.get(ext)
        if category:
            return category, ext
        else:
            # Try mime-based guess for uncommon extensions
            category_by_mime = guess_category_by_mime(path)
            if category_by_mime != "Others":
                return category_by_mime, (ext or "unknown")
            return "Others", ext or "unknown"
    else:
        # No extension: try mime then fall back to Others
        category_by_mime = guess_category_by_mime(path)
        return category_by_mime, "no_ext"

def safe_destination(dest: Path, overwrite: bool) -> Path:
    """
    If dest exists and overwrite is False, append numeric suffix before extension:
    file.txt -> file (1).txt, file (2).txt, ...
    """
    if overwrite or not dest.exists():
        return dest

    parent = dest.parent
    stem = dest.stem
    suffix = dest.suffix
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def move_file(src: Path, dest: Path, dry_run: bool, overwrite: bool, verbose: bool) -> None:
    dest = safe_destination(dest, overwrite)
    if verbose or dry_run:
        print(f"{'DRY-RUN: would move' if dry_run else 'Moving'}: {src} -> {dest}")
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(src), str(dest))
    except Exception as e:
        print(f"Error moving {src} -> {dest}: {e}", file=sys.stderr)

def organize_directory(target: Path, recursive: bool = True, dry_run: bool = True,
                       overwrite: bool = False, verbose: bool = True, skip_hidden: bool = True) -> None:
    if not target.exists() or not target.is_dir():
        raise ValueError(f"Target must be an existing directory: {target}")

    # Choose iterator
    if recursive:
        iterator = target.rglob('*')
    else:
        iterator = target.iterdir()

    for p in iterator:
        # Skip directories
        if p.is_dir():
            continue
        # Optionally skip hidden files
        if skip_hidden and any(part.startswith('.') for part in p.parts):
            if verbose:
                print(f"Skipping hidden file: {p}")
            continue
        # Skip files inside the category folders (avoid moving moved files again)
        # If parent is one of category names, skip
        if p.parent == target:
            pass  # top-level files are fine
        else:
            # Determine if the file is already in a recognized category folder under the target
            rel = None
            try:
                rel = p.relative_to(target)
            except Exception:
                rel = None
            if rel and len(rel.parts) >= 2 and rel.parts[0] in set(EXTENSION_CATEGORIES.values()).union({"Documents","Images","Videos","Audio","Archives","Code","Others"}):
                if verbose:
                    # assume already organized
                    print(f"Skipping (already in category folder): {p}")
                continue

        category, ext_folder = get_category(p)
        # Build destination: <target>/<Category>/<ext_folder>/<filename>
        dest_dir = target / category / ext_folder
        dest = dest_dir / p.name
        move_file(p, dest, dry_run, overwrite, verbose)

def parse_args():
    parser = argparse.ArgumentParser(description="Organize files by format into categorized folders.")
    parser.add_argument("target", nargs="?", default=".", help="Target directory (default: current directory)")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan directories recursively")
    parser.add_argument("--no-recursive", dest="recursive", action="store_false", help="Do not scan recursively")
    parser.set_defaults(recursive=True)
    parser.add_argument("-n", "--dry-run", action="store_true", help="Show what would be done without moving files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite files with same name in destination")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files (default: skip hidden)")
    return parser.parse_args()

def main():
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    try:
        organize_directory(
            target=target,
            recursive=args.recursive,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            verbose=not args.quiet,
            skip_hidden=not args.include_hidden
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
