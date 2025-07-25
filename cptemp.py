#!/usr/bin/env python3

import os
import shutil


# Template and filenames
TEMPLATE_FILENAME = "0.Template.ipynb"
FILENAMES = ["1.Overview", "1.a", "2.b", "3.c", "4.d", "5.e"]
SEARCH_ROOT = os.path.expanduser("~/Workspace/jupyter")  # Change if needed

def find_project_dir(start_path, target_file):
    """
    Recursively search for the directory containing the given template file.
    """
    for root, dirs, files in os.walk(start_path):
        if target_file in files:
            return root
    return None


def cptemp(subdir):
    """
    Copies template file into a new subdirectory with renamed notebook files.
    
    Args:
        subdir (str): Subdirectory name to create under the project directory.
    
    Returns:
        str: Status message for display or logging.
    """
    project_dir = find_project_dir(SEARCH_ROOT, TEMPLATE_FILENAME)
    if not project_dir:
        return f"❌ Could not find '{TEMPLATE_FILENAME}' under {SEARCH_ROOT}"

    source_file = os.path.join(project_dir, TEMPLATE_FILENAME)
    dest_dir = os.path.join(project_dir, subdir)

    os.makedirs(dest_dir, exist_ok=True)

    for name in FILENAMES:
        dest_path = os.path.join(dest_dir, f"{name}.ipynb")
        shutil.copy(source_file, dest_path)

    return f"✅ Copied template into: {dest_dir}"


# CLI interface
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: cptemp <destination-subdir>")
        sys.exit(1)

    subdir = sys.argv[1]
    result = cptemp(subdir)
    print(result)