# term_magic.py
# -*- coding: utf-8 -*-
from IPython.core.magic import register_line_magic
from IPython import get_ipython
import os
import yaml

# Optional: keep your existing helper
try:
    from cptemp import cptemp
except Exception:
    cptemp = None

TEMPLATE_PATH = os.path.expanduser("~/scripts/jupyter_helpers/terms_template.yaml")

# --- Utilities ----------------------------------------------------------------

def _load_templates():
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"❌ Template YAML file not found: {TEMPLATE_PATH}")
    with open(TEMPLATE_PATH, "r") as f:
        data = yaml.safe_load(f) or {}

    # Expected keys:
    # - template_term: {h: str, ex: str, n: str, fo: str}
    # - template_math: str
    # - template_func: str
    if "template_term" not in data:
        raise KeyError("❌ 'template_term' missing in YAML.")
    if not isinstance(data["template_term"], dict):
        raise TypeError("❌ 'template_term' must be a mapping with keys h, ex, n, fo.")
    for k in ("h", "ex", "n", "fo"):
        if k not in data["template_term"]:
            raise KeyError(f"❌ 'template_term.{k}' missing in YAML.")

    if "template_math" not in data:
        raise KeyError("❌ 'template_math' missing in YAML.")

    if "template_func" not in data:
        raise KeyError("❌ 'template_func' missing in YAML.")

    return data

def _set_next_cell(text: str):
    ip = get_ipython()
    if not ip:
        print("❌ Not running inside IPython.")
        return
    # Insert as a NEW cell below
    ip.set_next_input(text, replace=False)

def _clean_term_name(name: str) -> str:
    return name.strip()

def _render_placeholders(template: str, mapping: dict) -> str:
    # Very light templating: only replace a few known keys, leave the rest as-is
    out = template
    for key, val in mapping.items():
        out = out.replace(f"{{{{{key}}}}}", val)
    return out

def _compose_template_term_block(block_keys, templates_term, term_value=""):
    """
    block_keys: iterable of keys among ('h','ex','n','fo')
    templates_term: dict with keys 'h','ex','n','fo'
    term_value: value to inject into {{Term}}
    """
    pieces = []
    for k in block_keys:
        raw = templates_term[k]
        rendered = _render_placeholders(raw, {
            "Term": term_value or "{{Term}}"
        })
        pieces.append(rendered.rstrip())
    return "\n\n".join(pieces).rstrip() + "\n"

def _compose_template_math(template_math: str, term_value: str = "") -> str:
    return _render_placeholders(template_math, {
        "Term": term_value or "{{Term}}"
    }).rstrip() + "\n"

def _compose_template_func(template_func: str, func_name: str = "", module_path: str = "") -> str:
    # Best effort: fill FunctionName and ModulePath if provided
    mapping = {
        "FunctionName": func_name or "{{FunctionName}}",
        "ModulePath": module_path or "{{ModulePath}}"
    }
    return _render_placeholders(template_func, mapping).rstrip() + "\n"

def _parse_terms_arg(line: str):
    """
    Returns a dict:
      {
        'mode': 't1'|'t2'|'t3',      # t1 = template_term, t2 = template_math, t3 = template_func
        'blocks': ['h','ex','n','fo'] or subset for t1,
        'items': ['term1','term2', ...]   # or [] if using count
        'count': int or None,
        'module_hint': str or ""         # for t3 optional second token like numpy.linalg
      }
    Accepted forms:
      %terms                             -> full template_term (h+ex+n+fo) with one blank block
      %terms h,ex                        -> only header+example blocks (blank term)
      %terms Vector                      -> full template_term for "Vector"
      %terms h Vector,Matrix             -> only header block for both terms
      %terms 3                           -> insert 3 blank full template_term entries
      %terms t2                          -> template_math blank
      %terms t2 Probability,Variance     -> template_math for two terms
      %terms t3                          -> template_func blank
      %terms t3 mean numpy               -> template_func with FunctionName=mean, ModulePath=numpy
      %terms t3 polyfit numpy.polynomial -> template_func with FunctionName=polyfit, ModulePath=numpy.polynomial
    """
    s = (line or "").strip()
    if not s:
        return {"mode": "t1", "blocks": ["h","ex","n","fo"], "items": [], "count": 1, "module_hint": ""}

    # Mode shortcuts
    tokens = s.split()
    first = tokens[0].lower()

    # Detect t2/t3 modes
    if first in ("t2", "t3"):
        mode = first
        rest = s[len(first):].strip()
        if not rest:
            return {"mode": mode, "blocks": [], "items": [], "count": 1, "module_hint": ""}

        # For t3, allow: "t3 func [module.path]"
        if mode == "t3":
            parts = [p for p in rest.split() if p.strip()]
            if len(parts) == 1:
                return {"mode": "t3", "blocks": [], "items": [parts[0]], "count": None, "module_hint": ""}
            elif len(parts) >= 2:
                return {"mode": "t3", "blocks": [], "items": [parts[0]], "count": None, "module_hint": " ".join(parts[1:])}
        else:
            # t2 with comma list of terms
            items = [t for t in (p.strip() for p in rest.split(",")) if t]
            if len(items) == 1 and items[0].isdigit():
                return {"mode": "t2", "blocks": [], "items": [], "count": int(items[0]), "module_hint": ""}
            return {"mode": "t2", "blocks": [], "items": items, "count": None, "module_hint": ""}

    # Otherwise template_term (t1)
    # Check if it starts with block selectors
    if first in ("h", "ex", "n", "fo"):
        # allow comma separated block list in the first token OR across multiple tokens
        # e.g., "h,ex term1,term2"
        block_token = tokens[0]
        block_list = [b.strip().lower() for b in block_token.split(",") if b.strip()]
        rest = s[len(block_token):].strip()
        # remaining are item terms (comma-separated) OR a single integer count
        if not rest:
            return {"mode": "t1", "blocks": block_list, "items": [], "count": 1, "module_hint": ""}
        # If numeric, it's a count
        if rest.isdigit():
            return {"mode": "t1", "blocks": block_list, "items": [], "count": int(rest), "module_hint": ""}
        items = [t for t in (p.strip() for p in rest.split(",")) if t]
        return {"mode": "t1", "blocks": block_list, "items": items, "count": None, "module_hint": ""}

    # If single integer → N blank full entries
    if s.isdigit():
        return {"mode": "t1", "blocks": ["h","ex","n","fo"], "items": [], "count": int(s), "module_hint": ""}

    # Else, treat as comma-separated terms with full blocks
    items = [t for t in (p.strip() for p in s.split(",")) if t]
    return {"mode": "t1", "blocks": ["h","ex","n","fo"], "items": items, "count": None, "module_hint": ""}

def activate():
    ip = get_ipython()
    if not ip:
        print("❌ Not running inside IPython.")
        return

    @register_line_magic
    def cp_jup_temp(line):
        """Create templated notebooks via cptemp."""
        if cptemp is None:
            print("❌ cptemp not available. Ensure it is importable.")
            return
        folder = (line or "").strip()
        if not folder:
            print("❌ Usage: %cp_jup_temp <FolderName>")
            return
        try:
            cptemp(folder)
            print(f"✅ Created template notebooks in '{folder}'.")
        except Exception as e:
            print(f"❌ cptemp error: {e}")

    @register_line_magic
    def terms(line):
        """
        Insert study-note templates into the next cell.

        Usage (template_term):
          %terms                         # full (h+ex+n+fo), 1 blank
          %terms 3                       # full, 3 blanks
          %terms Vector,Matrix           # full for each term
          %terms h                       # header only, 1 blank
          %terms h 2                     # header only, 2 blanks
          %terms h Vector,Matrix         # header only for each term
          %terms h,ex Vector             # header+example for 'Vector'

        Usage (template_math):
          %terms t2                      # 1 blank
          %terms t2 Probability,Variance # one per term
          %terms t2 2                    # 2 blanks

        Usage (template_func):
          %terms t3                      # 1 blank
          %terms t3 mean                 # FunctionName=mean
          %terms t3 polyfit numpy        # FunctionName=polyfit, ModulePath=numpy
          %terms t3 dot numpy.linalg     # FunctionName=dot, ModulePath=numpy.linalg
        """
        try:
            data = _load_templates()
        except Exception as e:
            print(e)
            return

        args = _parse_terms_arg(line)

        mode = args["mode"]          # 't1' | 't2' | 't3'
        blocks = args["blocks"]      # for t1 only
        items = args["items"]        # list of terms or function names
        count = args["count"]        # int or None
        module_hint = args["module_hint"]

        out_chunks = []

        if mode == "t1":
            # template_term with block selection
            T = data["template_term"]
            block_keys = blocks or ["h","ex","n","fo"]

            if count is not None and count > 0:
                for _ in range(count):
                    out_chunks.append(_compose_template_term_block(block_keys, T, term_value=""))
            elif items:
                for term in items:
                    out_chunks.append(_compose_template_term_block(block_keys, T, term_value=_clean_term_name(term)))
            else:
                out_chunks.append(_compose_template_term_block(block_keys, T, term_value=""))

        elif mode == "t2":
            # template_math
            T = data["template_math"]
            if count is not None and count > 0:
                for _ in range(count):
                    out_chunks.append(_compose_template_math(T, term_value=""))
            elif items:
                for term in items:
                    out_chunks.append(_compose_template_math(T, term_value=_clean_term_name(term)))
            else:
                out_chunks.append(_compose_template_math(T, term_value=""))

        elif mode == "t3":
            # template_func
            T = data["template_func"]
            if items:
                func = _clean_term_name(items[0])
                mp   = module_hint.strip()
                out_chunks.append(_compose_template_func(T, func_name=func, module_path=mp))
            else:
                # count is supported but uncommon; default to 1
                n = count if (count and count > 0) else 1
                for _ in range(n):
                    out_chunks.append(_compose_template_func(T, func_name="", module_path=""))

        final_text = "\n".join(chunk.rstrip() for chunk in out_chunks).rstrip() + "\n"
        _set_next_cell(final_text)
        print("✅ Inserted template into the next cell.")

# If imported, auto-activate only when explicitly called by user:
# from term_magic import activate; activate()
