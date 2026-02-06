#!/usr/bin/env python3
"""
AITool CLI - Command-line interface for working with aitool.json files

Commands:
    validate    - Validate aitool.json files against schema
    test        - Run contract tests defined in aitool.json
    init        - Create a new aitool.json template
    list        - List all tools in a registry
    info        - Show detailed information about a tool
    registry    - Manage tool registries
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional
import logging

# Import SDK (assumes aitool.py is in same directory or installed)
try:
    from aitool import Tool, ToolRegistry, ValidationError, load_tool, load_registry
except ImportError:
    print("Error: aitool SDK not found. Make sure aitool.py is installed.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_schema(schema_path: Optional[str] = None) -> dict:
    """Load JSON Schema for validation"""
    if schema_path:
        with open(schema_path, 'r') as f:
            return json.load(f)
    return None


def cmd_validate(args):
    """Validate an aitool.json file against schema"""
    filepath = Path(args.file)
    
    if not filepath.exists():
        logger.error(f"File not found: {filepath}")
        return 1
    
    try:
        tool = load_tool(filepath)
        schema = load_schema(args.schema) if args.schema else None
        
        if schema:
            tool.validate_spec(schema)
        
        logger.info(f"✓ {filepath.name} is valid")
        logger.info(f"  Tool: {tool.manifest.name} v{tool.manifest.version}")
        logger.info(f"  Category: {tool.manifest.category}")
        
        return 0
        
    except ValidationError as e:
        logger.error(f"✗ Validation failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return 1


def cmd_test(args):
    """Run contract tests for a tool"""
    filepath = Path(args.file)
    
    try:
        tool = load_tool(filepath)
        
        if 'testing' not in tool.spec:
            logger.warning("No tests defined in aitool.json")
            return 0
        
        testing = tool.spec['testing']
        contract_tests = testing.get('contract_tests', [])
        
        if not contract_tests:
            logger.warning("No contract tests defined")
            return 0
        
        logger.info(f"Running {len(contract_tests)} contract tests...")
        
        passed = 0
        failed = 0
        
        for test in contract_tests:
            test_name = test.get('name', 'unnamed')
            test_input = test.get('input', {})
            
            try:
                logger.info(f"  Running: {test_name}")
                
                # Validate input
                tool.validate_input(test_input)
                
                # Execute if not a mock test
                if not args.dry_run:
                    result = tool.execute(test_input, validate_output=True)
                    
                    # Check assertions
                    assertions = test.get('assertions', [])
                    for assertion in assertions:
                        # Simple assertion checking (can be enhanced)
                        if 'is array' in assertion:
                            field = assertion.split()[0].replace('response.', '')
                            if field in result and isinstance(result[field], list):
                                continue
                            else:
                                raise AssertionError(f"Assertion failed: {assertion}")
                
                logger.info(f"    ✓ {test_name} passed")
                passed += 1
                
            except Exception as e:
                logger.error(f"    ✗ {test_name} failed: {e}")
                failed += 1
        
        logger.info(f"\nResults: {passed} passed, {failed} failed")
        return 0 if failed == 0 else 1
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1


def cmd_init(args):
    """Create a new aitool.json template"""
    output_path = Path(args.output)
    
    template = {
        "aitool_version": "1.0.0",
        "manifest": {
            "id": f"com.company.{args.name.replace('_', '-')}",
            "name": args.name,
            "version": "0.1.0",
            "display_name": args.name.replace('_', ' ').title(),
            "description": "Description of what this tool does",
            "category": args.category,
            "tags": [],
            "provider": {
                "name": "Your Company",
                "contact": "tools@company.com"
            }
        },
        "capabilities": {
            "primary_function": "describe_primary_function",
            "supported_operations": [],
            "idempotent": True,
            "stateful": False,
            "requires_auth": False
        },
        "execution": {
            "protocol": "function_call",
            "endpoint": {
                "type": "python_function",
                "module": "your.module",
                "function": args.name
            },
            "parameters": {
                "type": "object",
                "required": [],
                "properties": {}
            },
            "returns": {
                "success_schema": {
                    "type": "object",
                    "properties": {}
                },
                "success_criteria": []
            },
            "timeout_seconds": 30
        },
        "usage_guidance": {
            "when_to_use": [
                {
                    "trigger": "Describe when to use this tool",
                    "confidence": "high",
                    "examples": []
                }
            ],
            "when_not_to_use": [],
            "best_practices": [],
            "common_mistakes": []
        },
        "error_handling": [],
        "examples": []
    }
    
    with open(output_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    logger.info(f"✓ Created template: {output_path}")
    logger.info(f"  Edit the file to complete the tool specification")
    
    return 0


def cmd_list(args):
    """List all tools in a registry"""
    directory = Path(args.directory)
    
    try:
        registry = load_registry(directory)
        tools = registry.list_tools()
        
        if not tools:
            logger.info("No tools found")
            return 0
        
        logger.info(f"Found {len(tools)} tools:\n")
        
        for tool_info in tools:
            print(f"  {tool_info['name']} (v{tool_info.get('version', 'unknown')})")
            print(f"    Category: {tool_info['category']}")
            print(f"    {tool_info['description'][:80]}...")
            print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        return 1


def cmd_info(args):
    """Show detailed information about a tool"""
    filepath = Path(args.file)
    
    try:
        tool = load_tool(filepath)
        
        print(f"\n{tool.manifest.display_name or tool.manifest.name}")
        print("=" * 60)
        print(f"ID:          {tool.manifest.id}")
        print(f"Version:     {tool.manifest.version}")
        print(f"Category:    {tool.manifest.category}")
        print(f"Description: {tool.manifest.description}\n")
        
        print("Capabilities:")
        print(f"  Primary:   {tool.capabilities['primary_function']}")
        print(f"  Idempotent: {tool.capabilities.get('idempotent', 'unknown')}")
        print(f"  Stateful:   {tool.capabilities.get('stateful', 'unknown')}")
        
        if 'operations' in tool.spec:
            ops = tool.spec['operations']
            if 'performance' in ops:
                perf = ops['performance']
                if 'latency_ms' in perf:
                    lat = perf['latency_ms']
                    print(f"\nPerformance:")
                    print(f"  p50: {lat.get('p50')}ms")
                    print(f"  p95: {lat.get('p95')}ms")
                    print(f"  p99: {lat.get('p99')}ms")
        
        if args.verbose:
            print(f"\nFull specification:")
            print(json.dumps(tool.spec, indent=2))
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to load tool info: {e}")
        return 1


def cmd_registry(args):
    """Manage tool registries"""
    if args.registry_command == 'create':
        registry_data = {
            "registry_version": "1.0.0",
            "last_updated": "2025-02-05T00:00:00Z",
            "description": "Tool registry",
            "tools": [],
            "categories": {}
        }
        
        output = Path(args.output)
        with open(output, 'w') as f:
            json.dump(registry_data, f, indent=2)
        
        logger.info(f"✓ Created registry: {output}")
        return 0
    
    elif args.registry_command == 'update':
        # Scan directory and update registry
        directory = Path(args.directory)
        registry_file = directory / "registry.json"
        
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry_data = json.load(f)
        else:
            registry_data = {
                "registry_version": "1.0.0",
                "tools": [],
                "categories": {}
            }
        
        # Scan for aitool.json files
        tool_files = list(directory.glob("*.aitool.json"))
        logger.info(f"Found {len(tool_files)} tool files")
        
        registry_data['tools'] = []
        for tool_file in tool_files:
            try:
                tool = load_tool(tool_file)
                registry_data['tools'].append({
                    "id": tool.manifest.id,
                    "name": tool.manifest.name,
                    "version": tool.manifest.version,
                    "display_name": tool.manifest.display_name,
                    "category": tool.manifest.category,
                    "aitool_file": f"./{tool_file.name}",
                    "status": "active"
                })
            except Exception as e:
                logger.warning(f"Skipped {tool_file.name}: {e}")
        
        with open(registry_file, 'w') as f:
            json.dump(registry_data, f, indent=2)
        
        logger.info(f"✓ Updated registry with {len(registry_data['tools'])} tools")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='AITool CLI - Manage aitool.json files',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # validate command
    validate_parser = subparsers.add_parser('validate', help='Validate an aitool.json file')
    validate_parser.add_argument('file', help='Path to aitool.json file')
    validate_parser.add_argument('--schema', help='Path to JSON schema file')
    
    # test command
    test_parser = subparsers.add_parser('test', help='Run contract tests')
    test_parser.add_argument('file', help='Path to aitool.json file')
    test_parser.add_argument('--dry-run', action='store_true', help='Validate tests without executing')
    
    # init command
    init_parser = subparsers.add_parser('init', help='Create new aitool.json template')
    init_parser.add_argument('name', help='Tool name (snake_case)')
    init_parser.add_argument('--output', '-o', default='tool.aitool.json', help='Output file path')
    init_parser.add_argument('--category', '-c', default='other', 
                            choices=['data_retrieval', 'data_manipulation', 'communication',
                                    'computation', 'file_operations', 'api_integration',
                                    'automation', 'monitoring', 'security', 'other'],
                            help='Tool category')
    
    # list command
    list_parser = subparsers.add_parser('list', help='List tools in registry')
    list_parser.add_argument('directory', help='Registry directory')
    
    # info command
    info_parser = subparsers.add_parser('info', help='Show tool information')
    info_parser.add_argument('file', help='Path to aitool.json file')
    info_parser.add_argument('--verbose', '-v', action='store_true', help='Show full specification')
    
    # registry command
    registry_parser = subparsers.add_parser('registry', help='Manage registries')
    registry_subparsers = registry_parser.add_subparsers(dest='registry_command')
    
    create_registry = registry_subparsers.add_parser('create', help='Create new registry')
    create_registry.add_argument('--output', '-o', default='registry.json', help='Output file')
    
    update_registry = registry_subparsers.add_parser('update', help='Update registry from directory')
    update_registry.add_argument('directory', help='Directory containing aitool.json files')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to appropriate command
    if args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'test':
        return cmd_test(args)
    elif args.command == 'init':
        return cmd_init(args)
    elif args.command == 'list':
        return cmd_list(args)
    elif args.command == 'info':
        return cmd_info(args)
    elif args.command == 'registry':
        return cmd_registry(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
