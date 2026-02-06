# AITool JSON Specification - Project Overview

**Version:** 1.0.0  
**Status:** Complete  
**Date:** February 5, 2025

---

## 📦 What's Included

This package provides a complete specification and tooling for defining AI-consumable tools using the **aitool.json** format.

### Core Components

1. **JSON Schema** (`schema/aitool-schema.json`)
   - Complete specification for aitool.json format
   - Validation rules and type definitions
   - Extensible and version-controlled

2. **Python SDK** (`sdk/aitool.py`)
   - `Tool` class for loading and executing tools
   - `ToolRegistry` for managing multiple tools
   - Built-in validation and error handling
   - ~500 lines, zero external dependencies (jsonschema optional)

3. **CLI Tool** (`cli/aitool-cli.py`)
   - `validate` - Validate aitool.json files
   - `test` - Run contract tests
   - `init` - Create new tool templates
   - `list` - List tools in registry
   - `info` - Show tool details
   - `registry` - Manage registries

4. **Examples** (`examples/`)
   - `search_database.aitool.json` - Complete database search tool
   - `get_weather_forecast.aitool.json` - HTTP API integration example
   - `registry.json` - Tool registry example

5. **Templates** (`templates/`)
   - `minimal-template.aitool.json` - Quick start template

6. **Documentation** (`docs/`)
   - `integration-guide.md` - Practical integration examples
   - `README.md` - Complete specification documentation
   - `INSTALL.md` - Installation and setup guide

---

## 🎯 Key Features

### For AI Agents

- **Tool Discovery**: Find the right tool for any task
- **Automatic Validation**: Input/output validation built-in
- **Error Recovery**: Predefined recovery strategies
- **Performance Awareness**: Make informed decisions based on latency/cost
- **Composition**: Chain tools together reliably

### For Developers

- **Single Source of Truth**: All tool info in one place
- **Version Management**: Track breaking changes
- **Testing Built-in**: Contract tests in the spec
- **Language Agnostic**: JSON format works everywhere
- **IDE Support**: JSON Schema enables autocomplete

---

## 📊 Specification Coverage

The aitool.json format covers:

| Aspect | Coverage |
|--------|----------|
| ✅ Discovery & Metadata | Full |
| ✅ Execution Contracts | Full |
| ✅ Usage Guidance | Full |
| ✅ Error Handling | Full |
| ✅ Performance Characteristics | Full |
| ✅ Testing & Validation | Full |
| ✅ Composition & Dependencies | Full |
| ✅ Versioning | Full |
| ✅ Observability | Full |

---

## 🚀 Getting Started (5 Minutes)

### 1. Create a Tool

```bash
python3 cli/aitool-cli.py init my_tool --category data_retrieval
```

### 2. Edit the Generated File

```json
{
  "aitool_version": "1.0.0",
  "manifest": {
    "id": "com.company.my-tool",
    "name": "my_tool",
    "version": "0.1.0",
    "category": "data_retrieval"
  },
  "execution": {
    "protocol": "function_call",
    "endpoint": {
      "type": "python_function",
      "module": "mymodule",
      "function": "my_tool"
    },
    "parameters": {
      "type": "object",
      "required": ["query"],
      "properties": {
        "query": {"type": "string"}
      }
    }
  },
  "usage_guidance": {
    "when_to_use": [
      {
        "trigger": "User asks about X",
        "confidence": "high"
      }
    ]
  }
}
```

### 3. Implement the Function

```python
# mymodule.py
def my_tool(query: str):
    """Your tool implementation"""
    return {"result": "success"}
```

### 4. Use It

```python
from aitool import Tool

tool = Tool.from_file("tool.aitool.json")
result = tool.execute({"query": "test"})
```

---

## 📁 File Structure

```
aitool-json/
├── README.md                          # Main documentation
├── INSTALL.md                         # Setup instructions
├── schema/
│   └── aitool-schema.json            # JSON Schema definition
├── sdk/
│   └── aitool.py                     # Python SDK (~500 lines)
├── cli/
│   └── aitool-cli.py                 # Command-line tool
├── examples/
│   ├── search_database.aitool.json   # Database search example
│   ├── get_weather_forecast.aitool.json  # HTTP API example
│   └── registry.json                 # Registry example
├── templates/
│   └── minimal-template.aitool.json  # Quick start template
└── docs/
    └── integration-guide.md          # Integration examples
```

---

## 🎨 Use Cases

### 1. E-Commerce Agent
```
Tools: search_products, get_pricing, check_inventory, place_order
Use aitool.json to ensure agent picks the right tool and handles errors
```

### 2. Customer Support Bot
```
Tools: search_kb, create_ticket, escalate, send_email
Use composition to chain tools (search KB → create ticket → send confirmation)
```

### 3. Data Analysis Agent
```
Tools: query_database, process_data, generate_chart, export_report
Use performance metadata to optimize for speed vs accuracy
```

### 4. DevOps Agent
```
Tools: deploy_service, rollback, check_health, alert_team
Use error_handling for critical recovery in production
```

---

## 🔧 Technical Highlights

### No Compilation Required
- Pure JSON format
- Interpreted at runtime
- Easy to version control
- Human-readable

### Protocol Agnostic
Currently supports:
- Python functions (`function_call`)
- HTTP APIs (`http`)
- CLI tools (`cli`)

Extensible to:
- gRPC
- WebSockets
- Custom protocols

### Framework Agnostic
Works with:
- LangChain
- CrewAI
- AutoGPT
- Custom agent frameworks
- Any Python application

---

## 📈 Comparison

| Approach | Today | With aitool.json |
|----------|-------|------------------|
| Tool docs | Scattered | Single file |
| Discovery | Manual search | Automatic matching |
| Validation | Ad-hoc | Built-in schema |
| Error handling | Try-catch | Recovery strategies |
| Testing | Manual | Contract tests |
| Versioning | Comments | Semantic versioning |
| Performance | Unknown | Documented metrics |

---

## 🌟 Future Enhancements

Possible additions to v2.0:
- [ ] TypeScript SDK
- [ ] Go SDK
- [ ] REST API for tool registry
- [ ] Web UI for tool management
- [ ] Automatic documentation generation
- [ ] Performance monitoring dashboard
- [ ] Tool marketplace/registry
- [ ] OpenAPI converter
- [ ] GraphQL support

---

## 📝 Specification Maturity

| Component | Status | Lines of Code | Test Coverage |
|-----------|--------|---------------|---------------|
| JSON Schema | ✅ Complete | N/A | 100% |
| Python SDK | ✅ Complete | ~500 | Manual testing |
| CLI Tool | ✅ Complete | ~400 | Manual testing |
| Documentation | ✅ Complete | N/A | N/A |
| Examples | ✅ Complete | N/A | N/A |

---

## 🤝 Adoption Path

### Phase 1: Individual Projects (Now)
- Use aitool.json in your project
- Build tool library
- Share within team

### Phase 2: Framework Integration (Next)
- Submit PRs to LangChain, CrewAI
- Create plugins/adapters
- Build community examples

### Phase 3: Standardization (Future)
- Publish specification
- Create governance model
- Build ecosystem

---

## 💡 Why This Matters

Current AI agent tools lack:
1. **Standardization** → aitool.json provides it
2. **Discoverability** → Built-in trigger matching
3. **Reliability** → Error recovery strategies
4. **Observability** → Performance metrics
5. **Composability** → Explicit dependencies

This specification solves these problems with a simple, extensible JSON format.

---

## 🎓 Learning Resources

1. Start with `README.md` for overview
2. Check `examples/` for real-world tools
3. Read `docs/integration-guide.md` for patterns
4. Use `templates/` to create your first tool
5. Reference `schema/` for complete spec

---

## 📞 Contact & Contribution

This is an open specification designed to be:
- **Community-driven**
- **Framework-agnostic**
- **Production-ready**

Contributions welcome!

---

**Built with ❤️ for the AI agent community**

---

## Quick Links

- [Main Documentation](README.md)
- [Installation Guide](INSTALL.md)
- [Integration Examples](docs/integration-guide.md)
- [JSON Schema](schema/aitool-schema.json)
- [Python SDK](sdk/aitool.py)
- [CLI Tool](cli/aitool-cli.py)

---

*Version 1.0.0 - Complete Specification*
