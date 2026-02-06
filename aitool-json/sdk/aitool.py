"""
AITool JSON SDK - Python Library for Working with aitool.json Files

This SDK provides classes and utilities for:
- Loading and validating aitool.json specifications
- Tool discovery and registry management
- Runtime tool execution with contract enforcement
- Error handling based on recovery strategies

Usage:
    from aitool import ToolRegistry, Tool
    
    # Load a single tool
    tool = Tool.from_file("search_database.aitool.json")
    
    # Load registry
    registry = ToolRegistry.from_directory("./tools")
    
    # Execute tool
    result = tool.execute({"query": "red shirts", "limit": 10})
"""

import json
import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time
import logging

try:
    from jsonschema import validate, ValidationError as JSONSchemaValidationError
except ImportError:
    JSONSchemaValidationError = Exception
    def validate(*args, **kwargs):
        pass  # Graceful degradation if jsonschema not installed


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Status of a tool in the registry"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    INACTIVE = "inactive"
    EXPERIMENTAL = "experimental"


class RecoveryStrategy(Enum):
    """Error recovery strategies"""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    WAIT_AND_RETRY = "wait_and_retry"
    ALTERNATE_TOOL = "alternate_tool"
    FAIL = "fail"
    PROMPT_USER = "prompt_user"


class ToolExecutionError(Exception):
    """Base exception for tool execution errors"""
    pass


class ValidationError(ToolExecutionError):
    """Raised when input validation fails"""
    pass


class TimeoutError(ToolExecutionError):
    """Raised when tool execution times out"""
    pass


class RateLimitError(ToolExecutionError):
    """Raised when rate limit is exceeded"""
    pass


@dataclass
class ToolManifest:
    """Tool manifest metadata"""
    id: str
    name: str
    version: str
    display_name: Optional[str]
    description: str
    category: str
    tags: List[str]
    provider: Dict[str, str]
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ToolManifest':
        return cls(
            id=data['id'],
            name=data['name'],
            version=data['version'],
            display_name=data.get('display_name'),
            description=data.get('description', ''),
            category=data['category'],
            tags=data.get('tags', []),
            provider=data.get('provider', {})
        )


@dataclass
class ErrorRecovery:
    """Error recovery configuration"""
    error_type: str
    error_code: Optional[str]
    strategy: RecoveryStrategy
    max_retries: Optional[int] = None
    backoff_ms: Optional[List[int]] = None
    wait_seconds: Optional[float] = None
    fallback_tool: Optional[str] = None
    message_to_user: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ErrorRecovery':
        recovery_data = data['recovery']
        return cls(
            error_type=data['error_type'],
            error_code=data.get('error_code'),
            strategy=RecoveryStrategy(recovery_data['strategy']),
            max_retries=recovery_data.get('max_retries'),
            backoff_ms=recovery_data.get('backoff_ms'),
            wait_seconds=recovery_data.get('wait_seconds'),
            fallback_tool=recovery_data.get('fallback_tool'),
            message_to_user=recovery_data.get('message_to_user')
        )


class Tool:
    """
    Represents an AITool with its complete specification.
    
    Handles loading, validation, and execution of tools defined in aitool.json format.
    """
    
    def __init__(self, spec: dict):
        """Initialize tool from specification dictionary"""
        self.spec = spec
        self.manifest = ToolManifest.from_dict(spec['manifest'])
        self.capabilities = spec['capabilities']
        self.execution = spec['execution']
        self.usage_guidance = spec['usage_guidance']
        self.error_handlers = [
            ErrorRecovery.from_dict(e) for e in spec.get('error_handling', [])
        ]
        self._cached_function = None
    
    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> 'Tool':
        """Load tool specification from aitool.json file"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Tool file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            spec = json.load(f)
        
        return cls(spec)
    
    @classmethod
    def from_dict(cls, spec: dict) -> 'Tool':
        """Create tool from dictionary specification"""
        return cls(spec)
    
    def validate_spec(self, schema: Optional[dict] = None) -> bool:
        """
        Validate tool specification against JSON Schema.
        
        Args:
            schema: Optional JSON Schema to validate against
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If specification is invalid
        """
        if schema:
            try:
                validate(instance=self.spec, schema=schema)
                logger.info(f"Tool {self.manifest.name} validated successfully")
                return True
            except JSONSchemaValidationError as e:
                raise ValidationError(f"Invalid tool specification: {e}")
        return True
    
    def validate_input(self, params: dict) -> bool:
        """
        Validate input parameters against tool's parameter schema.
        
        Args:
            params: Input parameters to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If parameters are invalid
        """
        param_schema = self.execution['parameters']
        
        try:
            validate(instance=params, schema=param_schema)
            return True
        except JSONSchemaValidationError as e:
            raise ValidationError(f"Invalid input parameters: {e}")
    
    def validate_output(self, result: Any) -> bool:
        """
        Validate output against tool's return schema.
        
        Args:
            result: Output to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If output is invalid
        """
        if 'returns' in self.execution and 'success_schema' in self.execution['returns']:
            success_schema = self.execution['returns']['success_schema']
            try:
                validate(instance=result, schema=success_schema)
                return True
            except JSONSchemaValidationError as e:
                logger.warning(f"Output validation failed: {e}")
                return False
        return True
    
    def _load_function(self):
        """Dynamically load the actual Python function"""
        if self._cached_function:
            return self._cached_function
        
        endpoint = self.execution['endpoint']
        
        if endpoint['type'] == 'python_function':
            module_name = endpoint['module']
            function_name = endpoint['function']
            
            try:
                module = importlib.import_module(module_name)
                self._cached_function = getattr(module, function_name)
                return self._cached_function
            except (ImportError, AttributeError) as e:
                raise ToolExecutionError(f"Could not load function {module_name}.{function_name}: {e}")
        else:
            raise NotImplementedError(f"Protocol {endpoint['type']} not yet supported")
    
    def execute(
        self,
        params: dict,
        validate_input: bool = True,
        validate_output: bool = True,
        handle_errors: bool = True
    ) -> Any:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Input parameters
            validate_input: Whether to validate inputs before execution
            validate_output: Whether to validate outputs after execution
            handle_errors: Whether to apply error recovery strategies
            
        Returns:
            Tool execution result
            
        Raises:
            ValidationError: If validation fails
            ToolExecutionError: If execution fails
        """
        # Validate inputs
        if validate_input:
            self.validate_input(params)
        
        # Load and execute function
        func = self._load_function()
        
        try:
            logger.info(f"Executing tool: {self.manifest.name}")
            result = func(**params)
            
            # Validate outputs
            if validate_output:
                self.validate_output(result)
            
            logger.info(f"Tool {self.manifest.name} executed successfully")
            return result
            
        except Exception as e:
            if handle_errors:
                return self._handle_error(e, params)
            else:
                raise
    
    def _handle_error(self, error: Exception, params: dict) -> Any:
        """
        Handle errors according to error_handling specification.
        
        Args:
            error: The exception that occurred
            params: Original parameters
            
        Returns:
            Result after recovery (if successful)
            
        Raises:
            Original error if no recovery possible
        """
        error_type = type(error).__name__
        
        # Find matching error handler
        handler = None
        for h in self.error_handlers:
            if h.error_code == error_type or h.error_type in str(error):
                handler = h
                break
        
        if not handler:
            logger.error(f"No error handler found for {error_type}")
            raise error
        
        logger.info(f"Handling error with strategy: {handler.strategy.value}")
        
        if handler.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            return self._retry_with_backoff(params, handler)
        
        elif handler.strategy == RecoveryStrategy.WAIT_AND_RETRY:
            if handler.message_to_user:
                logger.info(handler.message_to_user)
            time.sleep(handler.wait_seconds or 1)
            return self.execute(params, handle_errors=False)
        
        elif handler.strategy == RecoveryStrategy.PROMPT_USER:
            logger.warning(handler.message_to_user or str(error))
            raise error
        
        elif handler.strategy == RecoveryStrategy.FAIL:
            raise error
        
        else:
            raise error
    
    def _retry_with_backoff(self, params: dict, handler: ErrorRecovery) -> Any:
        """Retry execution with exponential backoff"""
        max_retries = handler.max_retries or 3
        backoff_ms = handler.backoff_ms or [1000, 2000, 4000]
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    sleep_ms = backoff_ms[min(attempt - 1, len(backoff_ms) - 1)]
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {sleep_ms}ms")
                    time.sleep(sleep_ms / 1000)
                
                return self.execute(params, handle_errors=False)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} retry attempts failed")
                    raise e
                continue
    
    def matches_trigger(self, user_query: str) -> bool:
        """
        Check if user query matches any of the tool's triggers.
        
        Args:
            user_query: User's natural language query
            
        Returns:
            True if query matches a trigger
        """
        triggers = self.usage_guidance.get('when_to_use', [])
        
        for trigger_spec in triggers:
            trigger = trigger_spec['trigger'].lower()
            examples = [ex.lower() for ex in trigger_spec.get('examples', [])]
            
            # Simple matching - can be enhanced with embeddings/semantic search
            if any(keyword in user_query.lower() for keyword in trigger.split()):
                return True
            
            if any(ex in user_query.lower() for ex in examples):
                return True
        
        return False
    
    def get_description(self) -> str:
        """Get human-readable tool description"""
        return f"{self.manifest.display_name or self.manifest.name}: {self.manifest.description}"
    
    def to_dict(self) -> dict:
        """Export tool specification as dictionary"""
        return self.spec


class ToolRegistry:
    """
    Registry for managing multiple tools.
    
    Provides tool discovery, loading, and selection capabilities.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.categories: Dict[str, List[str]] = {}
    
    @classmethod
    def from_directory(cls, directory: Union[str, Path]) -> 'ToolRegistry':
        """
        Load all aitool.json files from a directory.
        
        Args:
            directory: Path to directory containing aitool.json files
            
        Returns:
            Populated ToolRegistry
        """
        directory = Path(directory)
        registry = cls()
        
        # Look for registry.json first
        registry_file = directory / "registry.json"
        if registry_file.exists():
            registry.load_from_registry_file(registry_file)
        else:
            # Scan for individual aitool.json files
            for filepath in directory.glob("**/*.aitool.json"):
                try:
                    tool = Tool.from_file(filepath)
                    registry.register_tool(tool)
                    logger.info(f"Loaded tool: {tool.manifest.name}")
                except Exception as e:
                    logger.error(f"Failed to load tool from {filepath}: {e}")
        
        return registry
    
    def load_from_registry_file(self, filepath: Union[str, Path]):
        """Load tools from a registry.json file"""
        with open(filepath, 'r') as f:
            registry_data = json.load(f)
        
        base_dir = Path(filepath).parent
        
        for tool_info in registry_data['tools']:
            if tool_info['status'] == 'active':
                tool_file = base_dir / tool_info['aitool_file']
                try:
                    tool = Tool.from_file(tool_file)
                    self.register_tool(tool)
                except Exception as e:
                    logger.error(f"Failed to load {tool_info['name']}: {e}")
        
        self.categories = registry_data.get('categories', {})
    
    def register_tool(self, tool: Tool):
        """Register a tool in the registry"""
        self.tools[tool.manifest.id] = tool
        
        # Add to category
        category = tool.manifest.category
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(tool.manifest.id)
    
    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get tool by ID"""
        return self.tools.get(tool_id)
    
    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Get tool by function name"""
        for tool in self.tools.values():
            if tool.manifest.name == name:
                return tool
        return None
    
    def find_tools(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> List[Tool]:
        """
        Find tools matching criteria.
        
        Args:
            category: Filter by category
            tags: Filter by tags (must have all tags)
            query: Natural language query to match against triggers
            
        Returns:
            List of matching tools
        """
        results = []
        
        for tool in self.tools.values():
            # Category filter
            if category and tool.manifest.category != category:
                continue
            
            # Tags filter
            if tags and not all(tag in tool.manifest.tags for tag in tags):
                continue
            
            # Query matching
            if query and not tool.matches_trigger(query):
                continue
            
            results.append(tool)
        
        return results
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List all tools with basic info"""
        return [
            {
                'id': tool.manifest.id,
                'name': tool.manifest.name,
                'display_name': tool.manifest.display_name,
                'category': tool.manifest.category,
                'description': tool.manifest.description
            }
            for tool in self.tools.values()
        ]
    
    def get_categories(self) -> Dict[str, int]:
        """Get all categories with tool counts"""
        return {cat: len(tools) for cat, tools in self.categories.items()}


# Convenience functions
def load_tool(filepath: Union[str, Path]) -> Tool:
    """Load a single tool from file"""
    return Tool.from_file(filepath)


def load_registry(directory: Union[str, Path]) -> ToolRegistry:
    """Load tool registry from directory"""
    return ToolRegistry.from_directory(directory)


__all__ = [
    'Tool',
    'ToolRegistry',
    'ToolManifest',
    'ErrorRecovery',
    'RecoveryStrategy',
    'ToolStatus',
    'ToolExecutionError',
    'ValidationError',
    'TimeoutError',
    'RateLimitError',
    'load_tool',
    'load_registry',
]
