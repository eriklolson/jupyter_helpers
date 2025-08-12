# ~/scripts/jupyter_helpers/nb_search.py
import json
import re
from pathlib import Path

def find_underscore_notebooks(base_dir):
    """
    Find all .ipynb files inside directories starting with '_'.
    """
    base_dir = Path(base_dir).expanduser().resolve()
    notebooks = []

    for path in base_dir.rglob("*.ipynb"):
        # Check if any parent dir starts with '_'
        if any(part.startswith("_") for part in path.parts):
            notebooks.append(path)

    return notebooks


def search_notebooks(keyword, base_dir="."):
    """
    Search for keyword (case-insensitive) inside .ipynb files in dirs starting with '_'.

    Args:
        keyword (str): Keyword to search for (case-insensitive).
        base_dir (str): Base directory to search from.
    """
    notebooks = find_underscore_notebooks(base_dir)
    keyword_re = re.compile(re.escape(keyword), re.IGNORECASE)
    results = {}

    for nb_file in notebooks:
        try:
            with open(nb_file, "r", encoding="utf-8") as f:
                nb_data = json.load(f)
        except Exception as e:
            print(f"⚠ Could not read {nb_file}: {e}")
            continue

        matches = []
        for cell_idx, cell in enumerate(nb_data.get("cells", [])):
            if cell.get("cell_type") not in ("markdown", "code"):
                continue

            for line_idx, line in enumerate(cell.get("source", []), start=1):
                if keyword_re.search(line):
                    matches.append((cell_idx, line_idx, line.strip()))

        if matches:
            results[str(nb_file)] = matches

    return results


if __name__ == "__main__":
    base_dir = "~/Workspace/jupyter"  # Change if needed
    keyword = input("Enter keyword to search: ").strip()

    results = search_notebooks(keyword, base_dir)

    if not results:
        print(f"❌ No matches found for '{keyword}'.")
    else:
        for nb, matches in results.items():
            print(f"\n📓 Matches in: {nb}")
            for cell_idx, line_idx, line in matches:
                print(f"  - Cell {cell_idx} (line {line_idx}): {line}")
