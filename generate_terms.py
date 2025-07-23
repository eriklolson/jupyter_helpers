from IPython.core.magic import register_line_magic
from IPython import get_ipython

def _terms(line):
    try:
        count = int(line)
        ip = get_ipython()
        payload = ip.payload_manager

        full_block = ""
        for i in range(1, count + 1):
            block = f"""# {i}. ✅ **Term**

> {{Definition of the term goes here. Describe its meaning in both programming and mathematical or theoretical contexts if applicable. Use bold keywords and concise phrasing.}}

#### 🧮 Examples:

> <!-- **Subtitle** -->
```python
# Replace with relevant code

```

**Notes:**
- {{First relevant note or clarification about limitations, alternatives, or nuances.}}
- {{Second point, such as historical use, performance tips, or related terminology.}}

* * *"""
            full_block += block + "\n\n"

        payload.write_payload({
            "source": "set_next_input",
            "text": full_block,
            "replace": False
        })

        print("💡 Markdown inserted into next cell — manually change it to Markdown.")

    except ValueError:
        print("❌ Please enter a valid number.")

def activate():
    ip = get_ipython()
    ip.register_magic_function(_terms, 'line', 'terms')