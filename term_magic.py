# ~/scripts/jupyter_helpers/term_magic.py
# -*- coding: utf-8 -*-
"""
Jupyter line magics:
  - %terms [...]: insert templated Markdown term blocks from terms_template.yaml
      Usage:
        %terms numpy,array,vector           # default template (see 'template' in YAML)
        %terms 3                            # insert 3 blank blocks
        %terms t2 numpy,vector              # use 'template_math' for given terms
        %terms t3                           # insert one 'template_func' block
  - %cp_jup_temp <FolderName>: create templated notebook subdir via cptemp.cptemp()
  - %nb_search <keyword> [base_dir=~/Workspace/jupyter]:
        Search case-insensitively through all .ipynb files located in any directory
        whose path contains a segment starting with '_' (e.g., _MLGlossary/...)
"""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from IPython.core.magic import register_line_magic
from IPython.display import Javascript, display

# --- Optional helpers imported from sibling modules (expected in this project) ---
# cptemp: user-provided
try:
    from cptemp import cptemp  # noqa: F401
except Exception:
    cptemp = None

# nb_search helpers
def _find_underscore_notebooks(base_dir: str) -> List[Path]:
    base = Path(base_dir).expanduser().resolve()
    notebooks: List[Path] = []
    for path in base.rglob("*.ipynb"):
        # any path segment beginning with underscore qualifies
        if any(part.startswith("_") for part in path.parts):
            notebooks.append(path)
    return notebooks

def _search_notebooks_ci(keyword: str, base_dir: str) -> Dict[str, List[tuple]]:
    """
    Case-insensitive search inside markdown and code cells.
    Returns: {notebook_path: [(cell_index, line_number, line_text), ...]}
    """
    keyword_re = re.compile(re.escape(keyword), re.IGNORECASE)
    results: Dict[str, List[tuple]] = {}
    for nb_file in _find_underscore_notebooks(base_dir):
        try:
            with open(nb_file, "r", encoding="utf-8") as f:
                nb_data = json.load(f)
        except Exception as e:
            print(f"⚠ Could not read {nb_file}: {e}")
            continue

        matches: List[tuple] = []
        for cell_idx, cell in enumerate(nb_data.get("cells", [])):
            if cell.get("cell_type") not in ("markdown", "code"):
                continue
            for line_idx, line in enumerate(cell.get("source", []), start=1):
                if keyword_re.search(line):
                    matches.append((cell_idx, line_idx, line.rstrip()))
        if matches:
            results[str(nb_file)] = matches
    return results

# --- YAML template loading / rendering ---

def _load_terms_yaml(yaml_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the user's terms_template.yaml. Supports both top-level 'template:' (single)
    and multiple named templates like 'template', 'template_term', 'template_math', 'template_func'.
    """
    import yaml  # lazy import to keep dependency optional elsewhere
    default_path = Path("~/scripts/jupyter_helpers/terms_template.yaml").expanduser()
    path = Path(yaml_path).expanduser() if yaml_path else default_path
    if not path.exists():
        raise FileNotFoundError(f"terms_template.yaml not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data

def _select_template_block(data: Dict[str, Any], key_hint: str | None = None) -> str:
    """
    Select a template string from YAML.
    Priority:
      - key_hint in {'template', 'template_term', 'template_math', 'template_func'}
      - 'template' if present
      - else first string value in the YAML
    """
    preferred_keys = []
    if key_hint:
        preferred_keys.append(key_hint)
    preferred_keys.append("template")  # common default from user's spec

    for k in preferred_keys:
        if k in data and isinstance(data[k], str):
            return data[k]

    # fall back: find any first string template in mapping (e.g., data['template_term']['h'] etc)
    for v in data.values():
        if isinstance(v, str):
            return v

    # Some users split templates into sections (h/ex/n/fo). If so, stitch them if key_hint provided.
    if key_hint and key_hint in data and isinstance(data[key_hint], dict):
        # Attempt to join sections in a sensible order
        order = ["h", "ex", "n", "fo"]
        parts = []
        for sect in order:
            block = data[key_hint].get(sect)
            if isinstance(block, str):
                parts.append(block)
        if parts:
            return "\n".join(parts)

    raise ValueError("No string templates found in terms_template.yaml")

def _render(template: str, mapping: Dict[str, str]) -> str:
    """
    Very light mustache-style replacement: {{Key}} -> value (or unchanged if missing).
    """
    def repl(match):
        key = match.group(1).strip()
        return str(mapping.get(key, f"{{{{{key}}}}}"))
    return re.sub(r"\{\{\s*([^\}]+)\s*\}\}", repl, template)

def _insert_markdown_cell(md_text: str) -> None:
    """
    Insert a new Markdown cell BELOW the current cell and set its content to md_text.
    """
    # Escape JS string properly
    js = f"""
    var md = {json.dumps(md_text)};
    var cell = Jupyter.notebook.insert_cell_below('markdown');
    cell.set_text(md);
    cell.render();
    """
    display(Javascript(js))

# --- Public activation function + magics ---

def activate(terms_yaml_path: Optional[str] = None,
             default_base_dir: str = "~/Workspace/jupyter") -> None:
    """
    Register line magics into the current IPython session.
    - terms_yaml_path: custom path to terms_template.yaml (optional)
    - default_base_dir: base path for %nb_search (optional)
    """

    # Store defaults on function object to read inside closures
    activate._terms_yaml_path = terms_yaml_path
    activate._default_base_dir = default_base_dir

    @register_line_magic
    def terms(line: str = ""):
        """
        Insert term templates into a new Markdown cell.

        Usage:
          %terms numpy,array,vector          # uses 'template' (or first available)
          %terms 3                           # insert 3 blank/default blocks
          %terms t2 numpy,vector             # uses 'template_math'
          %terms t3                          # uses 'template_func' once
          %terms t1 5                        # uses 'template' 5 times

        Template key aliases:
          t1 -> 'template' or 'template_term' (if present)
          t2 -> 'template_math'
          t3 -> 'template_func'
        """
        line = (line or "").strip()

        # Parse possible leading template selector (t1/t2/t3) and the rest
        tmpl_key_map = {
            "t1": None,               # prefer 'template' (falls back automatically)
            "t2": "template_math",
            "t3": "template_func",
        }

        parts = line.split(maxsplit=1)
        key_hint = None
        rest = ""
        if parts and parts[0].lower() in tmpl_key_map:
            key_hint = tmpl_key_map[parts[0].lower()]
            rest = parts[1].strip() if len(parts) > 1 else ""
        else:
            rest = line

        # Load YAML and resolve the template string
        data = _load_terms_yaml(activate._terms_yaml_path)
        # If user prefers template_term as default, allow aliasing:
        if key_hint is None and "template" not in data and "template_term" in data:
            key_hint = "template_term"
        template_str = _select_template_block(data, key_hint)

        # Decide whether 'rest' is a number (count) or a comma list of terms
        count = 0
        terms_list: List[str] = []
        numeric = rest.isdigit()

        if numeric:
            count = int(rest)
            if count <= 0:
                print("Nothing to insert (count <= 0).")
                return
        else:
            # comma-separated terms; allow empty to insert one blank
            terms_list = [t.strip() for t in rest.split(",") if t.strip()] if rest else []
            if not terms_list:
                count = 1  # one blank block

        # Build final markdown (concatenate if multiple)
        blocks: List[str] = []
        if terms_list:
            for term in terms_list:
                mapping = {
                    "Term": term,
                    "FunctionName": term,
                    "ModulePath": "{{ModulePath}}",
                    "Description": "{{Description}}",
                    "CodeExample": "{{CodeExample}}",
                    "Code/ML Example": "{{Code/ML Example}}",
                    "Code/ML Definition": "{{Code/ML Definition}}",
                    "Math Definition": "{{Math Definition}}",
                    "Statistics Definition": "{{Statistics Definition}}",
                    "Note1": "{{Note1}}",
                    "Note2": "{{Note2}}",
                    "MethodName": "{{MethodName}}",
                    "MethodSignature": "{{MethodSignature}}",
                    "MethodDescription": "{{MethodDescription}}",
                    "ExampleCode": "{{ExampleCode}}",
                    "Default1": "{{Default1}}",
                    "Default2": "{{Default2}}",
                    "Param1": "{{Param1}}",
                    "Param2": "{{Param2}}",
                    "Param3": "{{Param3}}",
                    "Param4": "{{Param4}}",
                    "Param5": "{{Param5}}",
                    "Definition1": "{{Definition1}}",
                    "Definition2": "{{Definition2}}",
                }
                blocks.append(_render(template_str, mapping).rstrip())
        else:
            # insert 'count' blank/default blocks
            for _ in range(count):
                blocks.append(_render(template_str, {
                    "Term": "{{Term}}",
                    "FunctionName": "{{FunctionName}}",
                    "ModulePath": "{{ModulePath}}",
                    "Description": "{{Description}}",
                    "CodeExample": "{{CodeExample}}",
                    "Code/ML Example": "{{Code/ML Example}}",
                    "Code/ML Definition": "{{Code/ML Definition}}",
                    "Math Definition": "{{Math Definition}}",
                    "Statistics Definition": "{{Statistics Definition}}",
                    "Note1": "{{Note1}}",
                    "Note2": "{{Note2}}",
                    "MethodName": "{{MethodName}}",
                    "MethodSignature": "{{MethodSignature}}",
                    "MethodDescription": "{{MethodDescription}}",
                    "ExampleCode": "{{ExampleCode}}",
                    "Default1": "{{Default1}}",
                    "Default2": "{{Default2}}",
                    "Param1": "{{Param1}}",
                    "Param2": "{{Param2}}",
                    "Param3": "{{Param3}}",
                    "Param4": "{{Param4}}",
                    "Param5": "{{Param5}}",
                    "Definition1": "{{Definition1}}",
                    "Definition2": "{{Definition2}}",
                }).rstrip())

        final_md = "\n\n".join(blocks)
        # Ensure outer raw markdown block if user prefers to paste as raw md
        # (Not enforcing global wrapper here; templates themselves usually contain code-fences.)
        _insert_markdown_cell(final_md)
        print(f"✅ Inserted {len(blocks)} template block(s).")

    @register_line_magic
    def cp_jup_temp(line: str = ""):
        """
        Create a Jupyter subdirectory with templated notebooks.
        Usage:
          %cp_jup_temp 01.Intro
        """
        target = (line or "").strip()
        if not target:
            print("❌ Please provide a folder name. Example: %cp_jup_temp 01.Intro")
            return
        if cptemp is None:
            print("❌ cptemp module not found. Ensure it is importable from this kernel.")
            return
        try:
            cptemp(target)
            print(f"✅ Created templated notebooks in: {target}")
        except Exception as e:
            print(f"⚠ Error creating notebooks: {e}")

    @register_line_magic
    def nb_search(line: str = ""):
        """
        Search all .ipynb files inside directories whose path contains any segment
        starting with '_' (e.g., _MLGlossary/) for a case-insensitive keyword.

        Usage:
          %nb_search keyword
          %nb_search "predict_proba"
          %nb_search keyword base_dir=~/Workspace/jupyter
        """
        line = (line or "").strip()
        if not line:
            print("❌ Usage: %nb_search <keyword> [base_dir=~/Workspace/jupyter]")
            return

        # Parse optional base_dir=...
        base_dir = getattr(activate, "_default_base_dir", "~/Workspace/jupyter")
        m = re.search(r'\bbase_dir\s*=\s*([^\s]+)', line)
        if m:
            base_dir = m.group(1)

        # keyword is everything before base_dir=...
        keyword = line[: m.start()].strip() if m else line
        if not keyword:
            print("❌ Please provide a keyword to search.")
            return

        results = _search_notebooks_ci(keyword, base_dir)

        if not results:
            print(f"❌ No matches found for '{keyword}' under {Path(base_dir).expanduser().resolve()}")
            return

        # Pretty print results; also emit naive 'clickable' paths for some frontends
        for nb, matches in results.items():
            print(f"\n📓 {nb}")
            for cell_idx, line_idx, text in matches:
                # Trim overly long lines for console readability
                snippet = (text[:160] + "…") if len(text) > 160 else text
                print(f"  • Cell {cell_idx}, Line {line_idx}: {snippet}")

        print(f"\n✅ {sum(len(v) for v in results.values())} match(es) across {len(results)} notebook(s).")

# When imported in a Python session, users will call:
#   from term_magic import activate
#   activate()
# which registers the magics.
