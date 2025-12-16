#!/usr/bin/env python3
import argparse, os, subprocess
from pathlib import Path

def rsync_copy(src: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["rsync", "-a", "--delete", "--exclude", ".ipynb_checkpoints", f"{src}/", f"{dest}/"],
        check=True
    )

def nb_to_md_in_place(root: Path):
    """Convert all .ipynb files to Markdown in-place."""
    for ipynb in root.rglob("*.ipynb"):
        subprocess.run(
            ["jupyter", "nbconvert", "--to", "markdown", str(ipynb), "--output-dir", str(ipynb.parent)],
            check=True
        )

def fix_fences(root: Path):
    """Change ``` to ~~~~ in all Markdown files."""
    for md in root.rglob("*.md"):
        lines = []
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.startswith("```"):
                if line.strip() == "```":
                    lines.append("~~~~")
                else:
                    lang = line.strip()[3:]
                    lines.append(f"~~~~{lang}")
            else:
                lines.append(line)
        md.write_text("\n".join(lines) + "\n", encoding="utf-8")

def import_to_joplin(dest: Path, notebook: str, bigmem: bool):
    env = os.environ.copy()
    if bigmem:
        env["NODE_OPTIONS"] = "--max-old-space-size=8192"
    subprocess.run(
        ["joplin", "import", "--format", "md", "--recursive", "--destination", notebook, str(dest)],
        check=True,
        env=env
    )

def main():
    parser = argparse.ArgumentParser(
        description="Copy a directory, convert .ipynb → .md (~~~~ fences), and import to a Joplin notebook."
    )
    parser.add_argument("src", type=Path, help="Source folder containing Jupyter notebooks")
    parser.add_argument("dest", type=Path, help="Destination folder for converted Markdown")
    parser.add_argument(
        "-n", "--notebook", type=str, help="Target Joplin notebook name for import (creates it if missing)"
    )
    parser.add_argument("--bigmem", action="store_true", help="Use larger Node heap for big imports")
    args = parser.parse_args()

    rsync_copy(args.src, args.dest)
    nb_to_md_in_place(args.dest)
    fix_fences(args.dest)

    if args.notebook:
        import_to_joplin(args.dest, args.notebook, args.bigmem)
        print(f"[✓] Imported into Joplin notebook: {args.notebook}")
    else:
        print(f"[✓] Converted only — Markdown files in: {args.dest}")

if __name__ == "__main__":
    main()
