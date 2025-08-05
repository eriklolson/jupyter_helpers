from IPython.core.magic import register_line_magic
from IPython import get_ipython
import yaml
import os
from cptemp import cptemp as cptemp_fun  # alias for the imported function

# Run %terms pandas.iloc → inserts full assembled template with term filled in.
# Run %terms 3 → inserts 3 blank templates.
# Run %terms examples → inserts only the examples section from YAML.
# Run %terms notes → inserts only the notes section from YAML.

def activate():
    ip = get_ipython()

    @register_line_magic
    def terms(line):
        template_path = os.path.expanduser("~/scripts/jupyter_helpers/terms_template.yaml")
        if not os.path.exists(template_path):
            print(f"❌ Template YAML file not found: {template_path}")
            return

        with open(template_path, "r") as f:
            data = yaml.safe_load(f)
            template_data = data.get("template", {})
            if not isinstance(template_data, dict):
                print("❌ Template must now be a dict with sections (header, examples, notes, footer).")
                return

        # Determine if user requested a specific section
        section = None
        line_stripped = line.strip()
        if line_stripped.lower() in template_data.keys():
            section = line_stripped.lower()

        # Build the template string
        if section:
            # Only one section
            full_template = template_data.get(section, "").strip()
            terms_list = ["{{Term}}"]  # Single term placeholder
        else:
            # Assemble full template from all sections
            full_template = "\n".join([
                template_data.get("header", ""),
                template_data.get("examples", ""),
                template_data.get("notes", ""),
                template_data.get("footer", "")
            ]).strip()

            # Prepare term list
            try:
                count = int(line_stripped)
                terms_list = ["{{Term}}" for _ in range(count)]
            except ValueError:
                terms_list = [term.strip() for term in line_stripped.split(",") if term.strip()]

        # Build final output (no outer ```markdown)
        output = []
        for term in terms_list:
            filled = full_template.replace("{{Term}}", term)
            filled = filled.replace("```python", "````python").replace("```", "````")
            output.append(filled)

        ip.set_next_input("\n".join(output), replace=False)

    @register_line_magic
    def cptemp(line):
        subdir = line.strip()
        if not subdir:
            print("❌ Please provide a subdirectory name")
            return
        result = cptemp_fun(subdir)
        print(result)

    print("✅ Magics `%terms` and `%cptemp` activated.")