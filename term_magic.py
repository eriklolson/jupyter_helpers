from IPython.core.magic import register_line_magic
from IPython import get_ipython
import yaml
import os

@register_line_magic
def terms(line):
    ip = get_ipython()
    payload = ip.payload_manager

    # Load the markdown template from YAML
    template_path = os.path.expanduser("~/scripts/jupyter_helpers/terms_template.yaml")
    if not os.path.exists(template_path):
        print(f"❌ Template YAML file not found: {template_path}")
        return

    with open(template_path, "r") as f:
        data = yaml.safe_load(f)
        template = data.get("template", "").strip()
        if not template:
            print("❌ Template YAML missing or empty.")
            return

    line = line.strip()
    try:
        count = int(line)
        terms = [f"{{{{Term}}}}" for _ in range(count)]
    except ValueError:
        terms = [term.strip() for term in line.split(",") if term.strip()]

    full_block = ""
    for i, term in enumerate(terms, start=1):
        block = template
        block = block.replace("{{index}}", str(i))
        block = block.replace("{{Term}}", term)
        block = block.replace("{{Definition}}", "")
        block = block.replace("{{CodeExample}}", "")
        block = block.replace("{{MathExample}}", "")
        block = block.replace("{{Note1}}", "")
        block = block.replace("{{Note2}}", "")
        full_block += block + "\n\n"

    payload.write_payload({
        "source": "set_next_input",
        "text": full_block,
        "replace": False
    })

    print("💡 Markdown template(s) inserted into next cell — convert to Markdown and fill in.")

def activate():
    ip = get_ipython()
    ip.register_magic_function(terms, 'line')
