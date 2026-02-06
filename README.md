# aitool.json

A file format for describing AI tools so agents actually know how to use them.

## The Problem

Right now, if you want an AI agent to use your function, you basically write a docstring and hope for the best. The LLM reads it, makes a guess about what parameters to pass, calls your function, and maybe it works. 

When it fails, you have no idea why. Was the input wrong? Did it time out? Should it retry? The agent doesn't know either, so it just fails or halts or does something random.

This is fine for demos. It's terrible for production.

## What This Is

aitool.json is a way to describe tools that AI agents can actually use reliably. It's just a JSON file that lives next to your code and tells the agent:

- When to use this tool (and when NOT to)
- What parameters it needs and what format
- What it returns
- What to do when things go wrong
- How long it takes, how much it costs, rate limits, etc.

Think of it like an API spec, but for AI agents instead of developers.

## Example

Here's a minimal tool definition:

```json
{
  "aitool_version": "1.0.0",
  "manifest": {
    "id": "com.company.search-products",
    "name": "search_products",
    "version": "1.0.0",
    "description": "Search product database",
    "category": "data_retrieval"
  },
  "capabilities": {
    "primary_function": "search"
  },
  "execution": {
    "protocol": "function_call",
    "endpoint": {
      "type": "python_function",
      "module": "myapp.tools",
      "function": "search_products"
    },
    "parameters": {
      "type": "object",
      "required": ["query"],
      "properties": {
        "query": {
          "type": "string",
          "minLength": 3
        },
        "limit": {
          "type": "integer",
          "default": 10,
          "maximum": 100
        }
      }
    },
    "returns": {
      "success_schema": {
        "type": "object",
        "properties": {
          "results": {"type": "array"},
          "count": {"type": "integer"}
        }
      }
    }
  },
  "usage_guidance": {
    "when_to_use": [
      {
        "trigger": "User wants to find products",
        "examples": ["find red shirts", "search for laptops under $500"]
      }
    ],
    "when_not_to_use": [
      {
        "scenario": "User asks about prices",
        "reason": "Use get_pricing instead, this has stale data"
      }
    ]
  },
  "error_handling": [
    {
      "error_type": "timeout",
      "recovery": {
        "strategy": "retry_with_backoff",
        "max_retries": 3,
        "backoff_ms": [1000, 2000, 4000]
      }
    }
  ]
}
```

Now the agent knows:
- Call this when the user wants to search products
- The query must be at least 3 characters
- If it times out, retry with exponential backoff
- Don't use this for pricing questions

## What's in This Repo

```
aitool-json/
├── schema/
│   └── aitool-schema.json          # The actual spec (JSON Schema format)
│
├── sdk/
│   └── aitool.py                   # Python library to load and use these files
│
├── cli/
│   └── aitool-cli.py               # Command line tool
│
├── examples/
│   ├── search_database.aitool.json       # Full example with everything
│   ├── get_weather_forecast.aitool.json  # HTTP API example
│   └── registry.json                     # How to organize multiple tools
│
├── templates/
│   └── minimal-template.aitool.json      # Copy this to start a new tool
│
└── docs/
    └── integration-guide.md              # Code examples for real use
```

## Quick Start

### 1. Create a tool file

Copy the template:
```bash
cp templates/minimal-template.aitool.json my_tool.aitool.json
```

Edit it to describe your tool. Main things to fill in:
- `manifest` - name, description, category
- `execution.endpoint` - where your actual code lives
- `execution.parameters` - what inputs it takes
- `usage_guidance` - when to use it

### 2. Validate it

```bash
python3 cli/aitool-cli.py validate my_tool.aitool.json
```

### 3. Use it in code

```python
from aitool import Tool

tool = Tool.from_file("my_tool.aitool.json")
result = tool.execute({"query": "test", "limit": 5})
```

The SDK handles validation automatically. If the input is wrong, it fails fast with a clear error instead of calling your function with garbage.

## The Structure Explained

Every aitool.json file has these sections:

### manifest
Basic metadata. The `id` should be unique (use reverse domain notation). The `category` helps with discovery.

Categories:
- `data_retrieval` - fetch or search data
- `data_manipulation` - transform or process data  
- `communication` - send emails, messages, etc.
- `computation` - calculate stuff
- `file_operations` - work with files
- `api_integration` - external API calls
- `automation` - automate tasks
- `monitoring` - check status, health
- `security` - auth, permissions
- `other` - everything else

### capabilities
What the tool can do. Keep it simple. The `primary_function` is the one-word summary.

### execution
How to actually run it.

The `protocol` is usually `function_call` (a Python/JS/etc function) but can be `http` for APIs or `cli` for command-line tools.

The `endpoint` tells where to find it. For Python functions:
```json
"endpoint": {
  "type": "python_function",
  "module": "mypackage.tools",
  "function": "my_function"
}
```

The `parameters` use JSON Schema. If you've used OpenAPI/Swagger, it's the same thing.

### usage_guidance
This is the important part for AI agents.

`when_to_use` describes scenarios where this tool applies. Give examples of what users might say.

`when_not_to_use` is just as important. Tell the agent when to use a different tool instead.

`best_practices` and `common_mistakes` help the agent use the tool correctly.

### error_handling (optional but recommended)
Define what to do when things fail.

Recovery strategies:
- `retry` - just try again
- `retry_with_backoff` - wait longer between each retry
- `wait_and_retry` - wait a fixed time then retry once
- `alternate_tool` - use a different tool instead
- `fail` - give up and return error
- `prompt_user` - ask the user what to do

### operations (optional)
Performance characteristics like latency, cost, rate limits. Helps the agent make smart decisions.

### examples (optional but helpful)
Show real input/output pairs. Great for testing and documentation.

### composition (optional)
List other tools this depends on, or tools it works well with.

### versioning (optional)
Track breaking changes so agents know what version they're compatible with.

## Using the CLI

Check if a file is valid:
```bash
aitool-cli.py validate my_tool.aitool.json
```

Create a new tool from template:
```bash
aitool-cli.py init search_orders --category data_retrieval
```

Run the tests defined in the file:
```bash
aitool-cli.py test my_tool.aitool.json
```

List all tools in a directory:
```bash
aitool-cli.py list ./tools
```

Get info about a tool:
```bash
aitool-cli.py info my_tool.aitool.json
```

Create or update a registry:
```bash
aitool-cli.py registry update ./tools
```

## Using the Python SDK

### Load a single tool

```python
from aitool import Tool

tool = Tool.from_file("search_products.aitool.json")

# Execute with validation
result = tool.execute({
    "query": "red shirts",
    "limit": 10
})
```

### Load a registry of tools

```python
from aitool import ToolRegistry

# Load all .aitool.json files in a directory
registry = ToolRegistry.from_directory("./tools")

# Find tools by category
tools = registry.find_tools(category="data_retrieval")

# Find tools by query matching
tools = registry.find_tools(query="search for products")

# Get a specific tool
tool = registry.get_tool("com.company.search-products")
```

### Manual validation

```python
from aitool import Tool, ValidationError

tool = Tool.from_file("my_tool.aitool.json")

params = {"query": "test"}

# Validate before calling
try:
    tool.validate_input(params)
    result = tool.execute(params)
except ValidationError as e:
    print(f"Bad input: {e}")
```

## Real Example - Database Search Tool

See `examples/search_database.aitool.json` for a complete, real-world example with:
- Full parameter validation (query length, limits, filters)
- Multiple error handlers (timeout, rate limit, invalid input, etc.)
- Usage guidance (when to use, when not to)
- Performance metrics (latency, throughput)
- Example inputs and outputs
- Test cases

## Why Not Just Use Function Signatures?

Function signatures tell you the types. They don't tell you:
- When to call the function
- What to do when it fails
- What the rate limits are
- What other functions to use instead
- Whether empty results are normal or an error
- Whether it's safe to retry

aitool.json captures all of this.

## Why JSON?

- Every language can read it
- Standard tooling (JSON Schema, validators, etc.)
- Easy to version control
- No compilation needed
- Humans can read and edit it

We could have used YAML or TOML, but JSON Schema is already a standard, and most people know JSON.

## Integrating with LangChain, CrewAI, etc.

See `docs/integration-guide.md` for code examples. The basic idea:

1. Load your aitool.json files
2. Wrap them in your framework's tool format
3. Let the agent use them

The SDK does the validation and error handling automatically.

## Contributing

The spec is designed to be extensible. If you need fields we don't have, add them. The schema doesn't forbid extra fields.

If you find patterns that should be in the standard, let's discuss it.

## FAQ

**Do I have to fill in every field?**  
No. Only `manifest`, `capabilities`, `execution`, and `usage_guidance` are required. Everything else is optional.

**Can I use this with non-Python tools?**  
Yes. Change the `execution.protocol` to `http` or `cli` or add your own.

**Does this work with streaming responses?**  
Set `capabilities.supports_streaming = true` and handle it in your code.

**What about authentication?**  
Set `capabilities.requires_auth = true` and handle auth in your actual implementation.

**Can I have multiple tools in one file?**  
No. One file = one tool. Use a registry.json to organize multiple tools.

**What if my tool changes?**  
Update the version number and document breaking changes in the `versioning` section.

## License

MIT - use it however you want.
