# ~/scripts/jupyter_helpers/term_magic.py
# -*- coding: utf-8 -*-
"""
Jupyter line magics:
  - %terms [...]: insert templated Markdown term blocks from terms_template.yaml
      Usage:
        %terms numpy,array,vector           # default template (see 'template' or 'template_term' in YAML)
        %terms 3                            # insert 3 blank blocks
        %terms t2 numpy,vector              # use 'template_math' for given terms
        %terms t3                           # insert one 'template_func' block
        %terms t1 5                         # use default template 5 times
        %terms t4 Graph,Tree                # 'template_diagram' for given terms
        %terms t5 AVL,Red-Black             # NEW: 'template_tree' for given terms

      Section-only (from template_term):
        %terms h Term1,Term2                # insert only header block(s)
        %terms ex pandas                    # insert only example block
        %terms n 3                          # insert notes block 3 times (blank)
        %terms fo                           # insert footer once

      Section-only (from template_diagram):
        %terms h2 Graph                     # header/definition
        %terms di Tree                      # diagram block
        %terms n2 2                         # notes (count)
        %terms ex2                          # example block (1)
        %terms fo2                          # footer (1)

      NEW: Section-only (from template_tree):
        %terms trh AVL                      # tree header/definition
        %terms trd AVL                      # tree diagram
        %terms trp 2                        # properties (count)
        %terms tra 1                        # common applications (count)
        %terms tree                         # python example (1)
        %terms trt                          # time complexity notes (1)
        %terms trf                          # footer (1)

  - %cp_jup_temp <FolderName>: create templated notebook subdir via cptemp.cptemp()

  - %nb_search <keyword> [base_dir=~/Workspace/jupyter]:
        Search case-insensitively through all .ipynb files located in any directory
        whose path contains a segment starting with '_' (e.g., _MLGlossary/...)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from IPython.core.magic import register_line_magic
from IPython.display import display, Markdown
from IPython import get_ipython

# --- Optional helpers imported from sibling modules (expected in this project) ---
try:
    from cptemp import cptemp  # noqa: F401
except Exception:
    cptemp = None


# ---------------------------------------------------------------------
# Notebook search helpers
# ---------------------------------------------------------------------
def _find_underscore_notebooks(base_dir: str) -> List[Path]:
    base = Path(base_dir).expanduser().resolve()
    notebooks: List[Path] = []
    for path in base.rglob("*.ipynb"):
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


# ---------------------------------------------------------------------
# YAML template loading / rendering
# ---------------------------------------------------------------------
def _load_terms_yaml(yaml_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the user's terms_template.yaml. Supports:
      - single 'template' key (string)
      - multiple named templates: 'template_term', 'template_math', 'template_func', 'template_diagram', 'template_tree'
      - sectioned dicts:
          * template_term: h/ex/n/tc/fo (tc optional)
          * template_diagram: h2/di/n2/ex2/tc2/fo2 (tc2 optional)
          * template_tree: trh/trd/trp/tra/tree/trt/trf (trt optional)
    """
    import yaml  # lazy import
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
      - key_hint in {'template', 'template_term', 'template_math', 'template_func', 'template_diagram', 'template_tree'}
      - 'template' if present (single big block)
      - else stitch sections for known sectioned templates
      - else first string value in the YAML
    """
    preferred_keys: List[str] = []
    if key_hint:
        preferred_keys.append(key_hint)
    preferred_keys.append("template")

    for k in preferred_keys:
        if k in data and isinstance(data[k], str):
            return data[k]

    # If key_hint points to a sectioned dict, stitch it in the defined order
    if key_hint and key_hint in data and isinstance(data[key_hint], dict):
        order_map = {
            "template_term": ["h", "ex", "n", "tc", "fo"],            # 'tc' included if present
            "template_diagram": ["h2", "di", "n2", "ex2", "tc2", "fo2"],
            "template_tree": ["trh", "trd", "trp", "tra", "tree", "trt", "trf"],
        }
        order = order_map.get(key_hint, [])
        parts = []
        for sect in order:
            val = data[key_hint].get(sect)
            if isinstance(val, str):
                parts.append(val)
        if parts:
            return "\n".join(parts)

    # Otherwise, try stitching known sectioned templates in a sensible order
    if "template_term" in data and isinstance(data["template_term"], dict):
        order = ["h", "ex", "n", "tc", "fo"]
        parts = [data["template_term"].get(sect) for sect in order]
        parts = [p for p in parts if isinstance(p, str)]
        if parts:
            return "\n".join(parts)

    if "template_diagram" in data and isinstance(data["template_diagram"], dict):
        order = ["h2", "di", "n2", "ex2", "tc2", "fo2"]
        parts = [data["template_diagram"].get(sect) for sect in order]
        parts = [p for p in parts if isinstance(p, str)]
        if parts:
            return "\n".join(parts)

    if "template_tree" in data and isinstance(data["template_tree"], dict):
        order = ["trh", "trd", "trp", "tra", "tree", "trt", "trf"]
        parts = [data["template_tree"].get(sect) for sect in order]
        parts = [p for p in parts if isinstance(p, str)]
        if parts:
            return "\n".join(parts)

    # Fallback to the first string value
    for v in data.values():
        if isinstance(v, str):
            return v

    raise ValueError("No string templates found in terms_template.yaml")


def _select_template_section(data: Dict[str, Any], section: str) -> str:
    """
    Return a single section:
      - 'h'|'ex'|'n'|'fo' from template_term
      - 'h2'|'di'|'n2'|'ex2'|'fo2' from template_diagram
      - 'trh'|'trd'|'trp'|'tra'|'tree'|'trt'|'trf' from template_tree
    """
    # template_term sections
    tt = data.get("template_term")
    if isinstance(tt, dict) and section in {"h", "ex", "n", "fo", "tc"}:
        block = tt.get(section)
        if isinstance(block, str):
            return block

    # template_diagram sections
    td = data.get("template_diagram")
    if isinstance(td, dict) and section in {"h2", "di", "n2", "ex2", "fo2", "tc2"}:
        block = td.get(section)
        if isinstance(block, str):
            return block

    # template_tree sections
    ttree = data.get("template_tree")
    if isinstance(ttree, dict) and section in {"trh", "trd", "trp", "tra", "tree", "trt", "trf"}:
        block = ttree.get(section)
        if isinstance(block, str):
            return block

    raise ValueError(f"Section '{section}' not found or not a string in available templates")


def _render(template: str, mapping: Dict[str, str]) -> str:
    """Light mustache-style replacement: {{Key}} -> value (unchanged if missing)."""
    def repl(match):
        key = match.group(1).strip()
        return str(mapping.get(key, f"{{{{{key}}}}}"))
    return re.sub(r"\{\{\s*([^\}]+)\s*\}\}", repl, template)


# ---------------------------------------------------------------------
# Cell insertion (Lab-safe, no front-end JS)
# ---------------------------------------------------------------------
def _insert_markdown_cell(md_text: str) -> None:
    """
    Insert a new Markdown cell BELOW the current cell in a JupyterLab/Notebook-safe way,
    without relying on the front-end `Jupyter` JS object.
    """
    ip = get_ipython()
    if not ip or not hasattr(ip, "set_next_input"):
        print("⚠ Could not access IPython. Are you running inside Jupyter?")
        return
    md_magic_block = md_text
    ip.set_next_input(md_magic_block, replace=False)


# ---------------------------------------------------------------------
# Public activation function + magics
# ---------------------------------------------------------------------
def activate(terms_yaml_path: Optional[str] = None,
             default_base_dir: str = "~/Workspace/jupyter") -> None:
    """
    Register line magics into the current IPython session.
    - terms_yaml_path: custom path to terms_template.yaml (optional)
    - default_base_dir: base path for %nb_search (optional)
    """
    activate._terms_yaml_path = terms_yaml_path
    activate._default_base_dir = default_base_dir


# --- Magics ---
@register_line_magic
def terms(line: str = ""):
    """
    Insert term templates into a new Markdown cell.

    Defaults:
      - template_term: NO tc unless you append `tc`
      - template_diagram (t4): ALWAYS includes tc2 (if present)
      - template_tree (t5): ALWAYS includes trt (if present)

    Examples:
      %terms BinarySearchTree              # template_term (no tc)
      %terms BinarySearchTree tc           # template_term (with tc)
      %terms t4 Graph                      # template_diagram (with tc2 if present)
      %terms t5 AVL,Red-Black              # template_tree (with trt if present)

    Section-only:
      %terms h Term1,Term2
      %terms ex pandas
      %terms n 3
      %terms fo
      %terms h2 Graph
      %terms di Tree
      %terms n2 2
      %terms ex2
      %terms fo2
      %terms trh AVL
      %terms trd AVL
      %terms trp 2
      %terms tra
      %terms tree
      %terms trt
      %terms trf
    """
    line = (line or "").strip()

    tmpl_key_map = {
        "t1": None,                # prefer 'template'; else stitch 'template_term'
        "t2": "template_math",
        "t3": "template_func",
        "t4": "template_diagram",
        "t5": "template_tree",     # NEW
    }
    section_keys = {
        "h", "ex", "n", "fo",
        "h2", "di", "n2", "ex2", "fo2",
        "trh", "trd", "trp", "tra", "tree", "trt", "trf"  # NEW
    }

    parts = line.split(maxsplit=1)
    key_hint = None
    rest = ""
    section_hint = None

    if parts:
        head = parts[0].lower()
        if head in section_keys:
            section_hint = head
            rest = parts[1].strip() if len(parts) > 1 else ""
        elif head in tmpl_key_map:
            key_hint = tmpl_key_map[head]
            rest = parts[1].strip() if len(parts) > 1 else ""
        else:
            rest = line
    else:
        rest = ""

    data = _load_terms_yaml(getattr(activate, "_terms_yaml_path", None))

    # Parse trailing toggle ONLY for template_term; diagram/tree always include tc2/trt by default if present.
    include_tc_term = False
    if rest:
        ws_parts = rest.split()
        if ws_parts and ws_parts[-1].lower() == "tc":
            include_tc_term = True
            rest_wo_toggle = " ".join(ws_parts[:-1]).strip()
        else:
            rest_wo_toggle = rest
    else:
        rest_wo_toggle = ""

    # Parse terms or count
    if rest_wo_toggle.isdigit():
        count = int(rest_wo_toggle)
        if count <= 0:
            print("Nothing to insert (count <= 0).")
            return
        terms_list = []
    else:
        terms_list = [t.strip() for t in rest_wo_toggle.split(",") if t.strip()]
        count = 1 if not terms_list else 0

    # Section-only mode: ignore tc logic entirely
    if section_hint:
        template_str = _select_template_section(data, section_hint)
        active_template = "section"
    else:
        if key_hint is None and "template" not in data and "template_term" in data:
            key_hint = "template_term"
        active_template = key_hint or "template"

        if active_template == "template_term" and isinstance(data.get("template_term"), dict):
            order = ["h", "ex", "n", "fo"]
            if include_tc_term and "tc" in data["template_term"]:
                insert_idx = order.index("fo") if "fo" in order else len(order)
                order = order[:insert_idx] + ["tc"] + order[insert_idx:]
            parts_tm = [data["template_term"].get(sect) for sect in order]
            parts_tm = [p for p in parts_tm if isinstance(p, str)]
            if not parts_tm:
                raise ValueError("template_term is empty or missing sections")
            template_str = "\n".join(parts_tm)

        elif active_template == "template_diagram" and isinstance(data.get("template_diagram"), dict):
            # ALWAYS include tc2 (before footer) if present
            order = ["h2", "di", "n2", "ex2", "fo2"]
            if "tc2" in data["template_diagram"]:
                insert_idx = order.index("fo2") if "fo2" in order else len(order)
                order = order[:insert_idx] + ["tc2"] + order[insert_idx:]
            parts_td = [data["template_diagram"].get(sect) for sect in order]
            parts_td = [p for p in parts_td if isinstance(p, str)]
            if not parts_td:
                raise ValueError("template_diagram is empty or missing sections")
            template_str = "\n".join(parts_td)

        elif active_template == "template_tree" and isinstance(data.get("template_tree"), dict):
            # ALWAYS include trt (before footer) if present
            order = ["trh", "trd", "trp", "tra", "tree", "trf"]
            if "trt" in data["template_tree"]:
                insert_idx = order.index("trf") if "trf" in order else len(order)
                order = order[:insert_idx] + ["trt"] + order[insert_idx:]
            parts_ttree = [data["template_tree"].get(sect) for sect in order]
            parts_ttree = [p for p in parts_ttree if isinstance(p, str)]
            if not parts_ttree:
                raise ValueError("template_tree is empty or missing sections")
            template_str = "\n".join(parts_ttree)

        else:
            template_str = _select_template_block(data, key_hint)

    # In _blank_mapping(), append these keys:
    def _blank_mapping() -> Dict[str, str]:
        return {
            "Term": "{{Term}}",
            "FunctionName": "{{FunctionName}}",
            "ModulePath": "{{ModulePath}}",
            "Description": "{{Description}}",
            "CodeExample": "{{CodeExample}}",
            "Code/ML Example": "{{Code/ML Example}}",
            "Code/ML Definition": "{{Code/ML Definition}}",
            "Math Definition": "{{Math Definition}}",
            "Statistics Definition": "{{Statistics Definition}}",
            "Diagram": "{{Diagram}}",
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
            "AverageCase": "{{AverageCase}}",
            "WorstCase": "{{WorstCase}}",
            "AverageName": "{{AverageName}}",
            "WorstName": "{{WorstName}}",
            "AverageSlug": "{{AverageSlug}}",
            "WorstSlug": "{{WorstSlug}}",
            # NEW for template_tree side-by-side diagrams:
            "TypeDistinguishingExample": "{{TypeDistinguishingExample}}",
            "TypeContradistinguishingExample": "{{TypeContradistinguishingExample}}",
        }
    blocks: List[str] = []
    if terms_list:
        for term in terms_list:
            mapping = _blank_mapping()
            mapping.update({"Term": term, "FunctionName": term})
            blocks.append(_render(template_str, mapping).rstrip())
    else:
        for _ in range(count):
            blocks.append(_render(template_str, _blank_mapping()).rstrip())

    final_md = "\n\n".join(blocks)
    _insert_markdown_cell(final_md)

    # Status message
    tc_msg = ""
    if active_template == "template_term" and include_tc_term:
        tc_msg = " with tc"
    elif active_template == "template_diagram" and "tc2" in data.get("template_diagram", {}):
        tc_msg = " with tc2"
    elif active_template == "template_tree" and "trt" in data.get("template_tree", {}):
        tc_msg = " with trt"
    print(f"✅ Inserted {len(blocks)} template block(s){tc_msg}.")


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

    base_dir = getattr(activate, "_default_base_dir", "~/Workspace/jupyter")
    m = re.search(r'\bbase_dir\s*=\s*([^\s]+)', line)
    if m:
        base_dir = m.group(1)

    keyword = line[: m.start()].strip() if m else line
    if not keyword:
        print("❌ Please provide a keyword to search.")
        return

    results = _search_notebooks_ci(keyword, base_dir)
    if not results:
        print(f"❌ No matches found for '{keyword}' under {Path(base_dir).expanduser().resolve()}")
        return

    def highlight_md(match):
        return f"<span style='color:red;font-weight:bold;'>{match.group(0)}</span>"

    output_lines = []
    for nb, matches in results.items():
        nb_dir = Path(nb).parent.name
        nb_name = Path(nb).name
        output_lines.append(f"### 📓 {nb_dir}/{nb_name}")
        for cell_idx, line_idx, text in matches:
            snippet = text.strip()
            snippet = re.sub(re.escape(keyword), highlight_md, snippet, flags=re.IGNORECASE)
            if len(snippet) > 160:
                snippet = snippet[:160] + "…"
            output_lines.append(f"- **Cell {cell_idx}, Line {line_idx}:** {snippet}")

    display(Markdown("\n".join(output_lines)))
    print(f"\n✅ {sum(len(v) for v in results.values())} match(es) across {len(results)} notebook(s).")


# When imported in a Python session, call:
#   from term_magic import activate
#   activate()
# to register the magics.
