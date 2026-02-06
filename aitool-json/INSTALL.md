# AITool JSON - Installation & Setup

## Installation

### Option 1: Direct SDK Usage (No Installation)

Copy the SDK file to your project:
```bash
cp sdk/aitool.py /path/to/your/project/
```

Then import:
```python
from aitool import Tool, ToolRegistry
```

### Option 2: pip install (Future)

Once published to PyPI:
```bash
pip install aitool-json
```

### Option 3: Development Install

```bash
git clone https://github.com/yourorg/aitool-json.git
cd aitool-json
pip install -e .
```

---

## Dependencies

### Required
- Python 3.7+
- `jsonschema` (for validation)

### Optional
- `requests` (for HTTP protocol tools)
- `langchain` (for LangChain integration)

Install dependencies:
```bash
pip install jsonschema requests
```

---

## Quick Setup

### 1. Create Tools Directory

```bash
mkdir -p my-project/tools
cd my-project/tools
```

### 2. Initialize First Tool

```bash
python3 /path/to/aitool-cli.py init search_products --category data_retrieval
```

This creates `tool.aitool.json`. Edit it to match your needs.

### 3. Implement Tool Function

```python
# mytools/search.py
def search_products(query: str, limit: int = 10):
    """Search products in database"""
    # Your implementation here
    return {
        "results": [...],
        "total_count": 42
    }
```

### 4. Update aitool.json

Edit the `execution.endpoint` section:
```json
"endpoint": {
  "type": "python_function",
  "module": "mytools.search",
  "function": "search_products"
}
```

### 5. Test Your Tool

```bash
python3 /path/to/aitool-cli.py validate tool.aitool.json
python3 /path/to/aitool-cli.py test tool.aitool.json --dry-run
```

### 6. Use in Code

```python
from aitool import Tool

tool = Tool.from_file("tool.aitool.json")
result = tool.execute({"query": "red shirts", "limit": 5})
print(result)
```

---

## Project Structure

```
my-project/
├── tools/
│   ├── registry.json
│   ├── search_products.aitool.json
│   ├── get_pricing.aitool.json
│   └── send_email.aitool.json
├── mytools/
│   ├── __init__.py
│   ├── search.py
│   ├── pricing.py
│   └── email.py
└── agent.py
```

---

## Environment Variables

For tools requiring authentication:

```bash
export WEATHER_API_KEY="your-api-key"
export DATABASE_URL="postgresql://..."
```

Access in tool implementation:
```python
import os

def get_weather(location: str):
    api_key = os.getenv("WEATHER_API_KEY")
    # Use api_key...
```

---

## Validation

Validate all tools in directory:
```bash
for file in tools/*.aitool.json; do
    python3 aitool-cli.py validate "$file"
done
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Validate Tools

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install jsonschema
      
      - name: Validate all tools
        run: |
          for file in tools/*.aitool.json; do
            python3 cli/aitool-cli.py validate "$file"
          done
      
      - name: Run contract tests
        run: |
          for file in tools/*.aitool.json; do
            python3 cli/aitool-cli.py test "$file" --dry-run
          done
```

---

## Troubleshooting

### Issue: "Module not found" when executing tool

**Solution**: Make sure the module path in `execution.endpoint.module` is correct and the module is in your Python path.

```python
import sys
sys.path.append('/path/to/your/modules')
```

### Issue: "Validation failed" for valid JSON

**Solution**: Check that all required fields are present. Use the schema for reference:
```bash
python3 aitool-cli.py validate tool.aitool.json --schema schema/aitool-schema.json
```

### Issue: Tool execution times out

**Solution**: Increase `execution.timeout_seconds` in your aitool.json:
```json
"execution": {
  "timeout_seconds": 60
}
```

---

## Support

- **Documentation**: See `/docs/` directory
- **Examples**: See `/examples/` directory
- **Issues**: GitHub Issues (when published)

---

## Next Steps

1. Read the [Integration Guide](docs/integration-guide.md)
2. Review [Example Tools](examples/)
3. Check out the [Schema](schema/aitool-schema.json)
4. Build your first AI agent!
