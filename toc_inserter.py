# jupyter_toc_inserter.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Iterable, Union
from IPython.display import Markdown, display
import os
import yaml
import re

_YAML_PATH = os.path.expanduser("~/scripts/jupyter_helpers/chapter_slugs.yaml")

# --- YAML LOADER HELPERS -----------------------------------------------------
def _load_yaml(yaml_path: str = _YAML_PATH) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data

def _slug_for_chapter(chapter: str, data: dict) -> str:
    """
    Resolve a display slug for a given chapter (e.g., 'Matplotlib' -> 'Matp').
    Falls back to the original chapter name if not present in YAML mappings.
    """
    # Try exact slug_to_dir reverse path first (when user passes a slug)
    slug_to_dir = data.get("slug_to_dir", {})
    dir_to_slug = data.get("dir_to_slug", {})

    # If chapter is one of the directory keys (e.g., "10.ML"), map to slug
    if chapter in dir_to_slug:
        return dir_to_slug[chapter]

    # If chapter matches an existing slug, keep it
    if chapter in slug_to_dir:
        return chapter

    # If chapter is like "Matplotlib" and a dir holds it, try matching by endswith
    # (e.g., "9.Matplotlib" -> "Matp")
    for dirname, slug in dir_to_slug.items():
        # dirname like "9.Matplotlib"
        if dirname.split(".", 1)[-1].lower() == chapter.lower():
            return slug

    # Fallback: keep original cleaned (letters/numbers only, preserve case)
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", chapter)
    return cleaned or chapter

# --- CORE TOC BUILDER --------------------------------------------------------
def insert_chapter_toc(
    chapter: str,
    submodules: Union[Dict[str, Iterable[str]], Iterable[str], None] = None,
    yaml_path: str = _YAML_PATH,
) -> None:
    """
    Insert a rendered Markdown Table of Contents in the Jupyter output area.

    Parameters
    ----------
    chapter : str
        Chapter display name (e.g., 'Matplotlib', 'SciPy', 'Pandas', 'Numpy', 'ML', 'DSA', etc.).
    submodules : dict | list | None
        - If dict: { "Sklearn": ["KNeighborsClassifier", "LogisticRegression"], ... }
        - If list/iterable: ["Sklearn", "XGBoost"]  (no class bullets)
        - If None: no submodule sections are shown.
    yaml_path : str
        Path to chapter_slugs.yaml (default: ~/scripts/jupyter_helpers/chapter_slugs.yaml)
    """
    data = _load_yaml(yaml_path)
    chapter_slug = _slug_for_chapter(chapter, data)

    special = {"Matplotlib", "SciPy", "Pandas", "Numpy"}

    lines: List[str] = []
    lines.append(f"# {chapter} Table of Contents")

    if chapter in special:
        # Normalize submodules into a dict[str, List[str]]
        if submodules is None:
            sub_dict: Dict[str, List[str]] = {}
        elif isinstance(submodules, dict):
            sub_dict = {k: list(v) for k, v in submodules.items()}
        else:
            sub_dict = {str(s): [] for s in submodules}

        for sub_name, classes in sub_dict.items():
            # Expected file: ./_{ChapterSlug}{SubName}.ipynb, e.g., ./_MLSklearn.ipynb
            nb_name = f"._{chapter_slug}{sub_name}.ipynb"  # leading dot was a typo risk; fix below
            nb_name = f"./_{chapter_slug}{sub_name}.ipynb"
            nb_path = Path(nb_name)

            if nb_path.exists():
                lines.append(f"## [{sub_name}]({nb_name}#table-of-contents)")
            else:
                lines.append(f"### {sub_name}")
                for cls in classes:
                    lines.append(f"- {cls}")
    else:
        lines.append("## Key Concepts")

    # Render as Markdown in the output cell
    display(Markdown("\n".join(lines)))

# --- EXAMPLE USAGE -----------------------------------------------------------
if __name__ == "__main__":
    # Example 1: Matplotlib with submodules, linking if notebook exists
    insert_chapter_toc(
        chapter="Matplotlib",
        submodules={
            "Pyplot": ["plot()", "scatter()", "bar()", "hist()", "imshow()"],
            "Artist": ["Text", "Line2D", "Patch", "AxesImage"],
        },
    )

    # Example 2: SciPy with just submodule names (no class bullets)
    insert_chapter_toc(
        chapter="SciPy",
        submodules=["Stats", "Optimize", "Signal"],
    )

    # Example 3: DSA (not in special set) → prints header + Key Concepts
    insert_chapter_toc(chapter="DSA")
