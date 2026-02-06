# AITool JSON Integration Examples

This document shows practical examples of integrating aitool.json into various AI agent frameworks and applications.

---

## 📚 Table of Contents

1. [Basic Python Integration](#basic-python-integration)
2. [LangChain Integration](#langchain-integration)
3. [Custom Agent Framework](#custom-agent-framework)
4. [Error Handling Patterns](#error-handling-patterns)
5. [Tool Discovery & Selection](#tool-discovery--selection)
6. [Production Deployment](#production-deployment)

---

## 1. Basic Python Integration

### Simple Tool Execution

```python
from aitool import Tool

# Load tool
tool = Tool.from_file("search_database.aitool.json")

# Execute with automatic validation
try:
    result = tool.execute({
        "query": "red shirts size M",
        "limit": 10
    })
    print(f"Found {result['total_count']} results")
    
except ValidationError as e:
    print(f"Invalid input: {e}")
    
except ToolExecutionError as e:
    print(f"Execution failed: {e}")
```

### With Manual Validation

```python
from aitool import Tool, ValidationError

tool = Tool.from_file("search_database.aitool.json")

params = {
    "query": "laptops",
    "limit": 50,
    "filters": {"category": "electronics"}
}

# Validate before execution
if tool.validate_input(params):
    result = tool.execute(params, validate_input=False)
    
    # Validate output
    if tool.validate_output(result):
        print("Success!")
```

---

## 2. LangChain Integration

### Creating LangChain Tools from aitool.json

```python
from langchain.tools import StructuredTool
from aitool import ToolRegistry
import json

class AIToolAdapter:
    """Adapter to use aitool.json tools in LangChain"""
    
    @staticmethod
    def to_langchain_tool(aitool):
        """Convert an AITool to LangChain StructuredTool"""
        
        def wrapped_function(**kwargs):
            """Wrapper that adds validation and error handling"""
            try:
                return aitool.execute(kwargs)
            except Exception as e:
                return {"error": str(e)}
        
        # Extract parameter schema
        param_schema = aitool.execution['parameters']
        
        # Create LangChain tool
        return StructuredTool(
            name=aitool.manifest.name,
            description=aitool.manifest.description,
            func=wrapped_function,
            args_schema=param_schema  # LangChain will use this for validation
        )

# Usage
registry = ToolRegistry.from_directory("./tools")
langchain_tools = []

for tool_id, aitool in registry.tools.items():
    lc_tool = AIToolAdapter.to_langchain_tool(aitool)
    langchain_tools.append(lc_tool)

# Now use with LangChain agent
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI

agent = initialize_agent(
    langchain_tools,
    OpenAI(temperature=0),
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

response = agent.run("Find me red shirts under $30")
```

---

## 3. Custom Agent Framework

### Building an AI Agent with Tool Selection

```python
from aitool import ToolRegistry
from typing import List, Dict, Any
import logging

class AIAgent:
    """Simple AI agent that uses aitool.json for tool discovery and execution"""
    
    def __init__(self, tools_directory: str):
        self.registry = ToolRegistry.from_directory(tools_directory)
        self.conversation_history = []
        self.logger = logging.getLogger(__name__)
    
    def select_tools(self, user_query: str) -> List:
        """Select relevant tools based on user query"""
        candidates = []
        
        for tool in self.registry.tools.values():
            if tool.matches_trigger(user_query):
                candidates.append(tool)
        
        # Sort by confidence if available
        return candidates
    
    def execute_tool(self, tool, params: Dict[str, Any]) -> Dict:
        """Execute tool with full error handling"""
        try:
            self.logger.info(f"Executing {tool.manifest.name}")
            
            result = tool.execute(params)
            
            return {
                "success": True,
                "result": result,
                "tool_used": tool.manifest.name
            }
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_used": tool.manifest.name
            }
    
    def process_query(self, user_query: str) -> Dict:
        """Main agent loop"""
        self.conversation_history.append({"role": "user", "content": user_query})
        
        # 1. Tool selection
        tools = self.select_tools(user_query)
        
        if not tools:
            return {"error": "No suitable tools found"}
        
        # 2. Extract parameters from query (simplified - in reality use LLM)
        params = self._extract_parameters(user_query, tools[0])
        
        # 3. Execute tool
        result = self.execute_tool(tools[0], params)
        
        self.conversation_history.append({"role": "assistant", "result": result})
        
        return result
    
    def _extract_parameters(self, query: str, tool) -> Dict:
        """Extract parameters from natural language query"""
        # Simplified - in production, use LLM to extract parameters
        # based on tool.execution['parameters'] schema
        
        param_schema = tool.execution['parameters']
        params = {}
        
        # Example: extract query parameter
        if 'query' in param_schema.get('properties', {}):
            params['query'] = query
        
        return params

# Usage
agent = AIAgent("./tools")
result = agent.process_query("Find me red shirts in stock")
print(result)
```

---

## 4. Error Handling Patterns

### Implementing Recovery Strategies

```python
from aitool import Tool, ErrorRecovery, RecoveryStrategy
import time

class ResilientToolExecutor:
    """Tool executor with sophisticated error handling"""
    
    def __init__(self, tool: Tool):
        self.tool = tool
        self.error_handlers = {handler.error_type: handler 
                              for handler in tool.error_handlers}
    
    def execute_with_recovery(self, params: Dict) -> Any:
        """Execute tool with automatic error recovery"""
        try:
            return self.tool.execute(params, handle_errors=False)
            
        except Exception as e:
            return self._recover_from_error(e, params)
    
    def _recover_from_error(self, error: Exception, params: Dict) -> Any:
        """Apply recovery strategy based on error type"""
        error_type = self._classify_error(error)
        
        if error_type not in self.error_handlers:
            raise error
        
        handler = self.error_handlers[error_type]
        strategy = handler.strategy
        
        print(f"Error detected: {error_type}")
        print(f"Applying recovery: {strategy.value}")
        
        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            return self._retry_with_backoff(params, handler)
        
        elif strategy == RecoveryStrategy.WAIT_AND_RETRY:
            time.sleep(handler.wait_seconds)
            return self.tool.execute(params, handle_errors=False)
        
        elif strategy == RecoveryStrategy.ALTERNATE_TOOL:
            return self._use_alternate_tool(handler.fallback_tool, params)
        
        elif strategy == RecoveryStrategy.PROMPT_USER:
            return {"error": handler.message_to_user, "retry_possible": True}
        
        else:
            raise error
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type"""
        error_name = type(error).__name__
        
        # Map exception types to error_types in aitool.json
        if "timeout" in error_name.lower():
            return "timeout"
        elif "rate" in error_name.lower() or "429" in str(error):
            return "rate_limit"
        elif "validation" in error_name.lower():
            return "invalid_input"
        else:
            return "unknown"
    
    def _retry_with_backoff(self, params: Dict, handler: ErrorRecovery) -> Any:
        """Retry with exponential backoff"""
        for attempt in range(handler.max_retries):
            try:
                if attempt > 0:
                    delay = handler.backoff_ms[min(attempt-1, len(handler.backoff_ms)-1)]
                    print(f"Retrying in {delay}ms...")
                    time.sleep(delay / 1000)
                
                return self.tool.execute(params, handle_errors=False)
                
            except Exception as e:
                if attempt == handler.max_retries - 1:
                    raise e
        
        raise Exception("All retries exhausted")
    
    def _use_alternate_tool(self, fallback_tool_id: str, params: Dict) -> Any:
        """Fall back to alternate tool"""
        # Load alternate tool from registry
        print(f"Falling back to: {fallback_tool_id}")
        # Implementation depends on having access to registry
        raise NotImplementedError("Fallback tool loading not implemented")

# Usage
tool = Tool.from_file("search_database.aitool.json")
executor = ResilientToolExecutor(tool)

result = executor.execute_with_recovery({
    "query": "red shirts",
    "limit": 10
})
```

---

## 5. Tool Discovery & Selection

### Smart Tool Selection Based on Context

```python
from aitool import ToolRegistry
from typing import List, Tuple
import re

class ToolSelector:
    """Intelligent tool selection engine"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    def select_best_tool(self, user_query: str, context: Dict = None) -> Tuple[Tool, float]:
        """
        Select the best tool for a query with confidence score
        
        Returns:
            (tool, confidence_score)
        """
        candidates = []
        
        for tool in self.registry.tools.values():
            score = self._score_tool(tool, user_query, context)
            if score > 0:
                candidates.append((tool, score))
        
        if not candidates:
            return None, 0.0
        
        # Return highest scoring tool
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]
    
    def _score_tool(self, tool, query: str, context: Dict = None) -> float:
        """
        Calculate relevance score for a tool
        
        Factors:
        - Trigger matching
        - Example matching
        - Category relevance
        - Anti-pattern avoidance
        - Performance characteristics
        """
        score = 0.0
        query_lower = query.lower()
        
        # Check triggers
        for trigger_spec in tool.usage_guidance.get('when_to_use', []):
            trigger = trigger_spec['trigger'].lower()
            confidence = trigger_spec.get('confidence', 'medium')
            
            # Keyword matching
            keywords = trigger.split()
            matches = sum(1 for kw in keywords if kw in query_lower)
            if matches > 0:
                base_score = matches / len(keywords)
                
                # Adjust by confidence
                multiplier = {'high': 1.0, 'medium': 0.7, 'low': 0.4}.get(confidence, 0.5)
                score += base_score * multiplier
            
            # Example matching
            for example in trigger_spec.get('examples', []):
                if example.lower() in query_lower:
                    score += 0.5
        
        # Check anti-patterns (reduce score if matched)
        for antipattern in tool.usage_guidance.get('when_not_to_use', []):
            scenario = antipattern['scenario'].lower()
            if any(word in query_lower for word in scenario.split()):
                score -= 0.3
        
        # Consider performance if context has latency requirements
        if context and 'max_latency_ms' in context:
            if 'operations' in tool.spec:
                perf = tool.spec['operations'].get('performance', {})
                tool_latency = perf.get('latency_ms', {}).get('p95', 1000)
                if tool_latency <= context['max_latency_ms']:
                    score += 0.2
                else:
                    score -= 0.2
        
        return max(0.0, score)
    
    def suggest_tools(self, user_query: str, top_k: int = 3) -> List[Tuple[Tool, float]]:
        """Get top-k tool suggestions with confidence scores"""
        scores = []
        
        for tool in self.registry.tools.values():
            score = self._score_tool(tool, user_query)
            if score > 0:
                scores.append((tool, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

# Usage
registry = ToolRegistry.from_directory("./tools")
selector = ToolSelector(registry)

# Find best tool
tool, confidence = selector.select_best_tool("Find me red shirts under $30")
print(f"Selected: {tool.manifest.name} (confidence: {confidence:.2f})")

# Get suggestions
suggestions = selector.suggest_tools("What's the weather in Paris?", top_k=3)
for tool, score in suggestions:
    print(f"  {tool.manifest.name}: {score:.2f}")
```

---

## 6. Production Deployment

### Monitoring and Observability

```python
from aitool import Tool, ToolRegistry
import time
from dataclasses import dataclass
from typing import Dict, List
import json
from datetime import datetime

@dataclass
class ToolMetrics:
    """Metrics for tool execution"""
    tool_name: str
    executions: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def success_rate(self) -> float:
        return self.successes / self.executions if self.executions > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.executions if self.executions > 0 else 0.0

class MonitoredToolRegistry(ToolRegistry):
    """Tool registry with built-in monitoring"""
    
    def __init__(self):
        super().__init__()
        self.metrics: Dict[str, ToolMetrics] = {}
    
    def execute_tool(self, tool_id: str, params: Dict) -> Dict:
        """Execute tool with monitoring"""
        tool = self.get_tool(tool_id)
        
        if not tool:
            raise ValueError(f"Tool not found: {tool_id}")
        
        # Initialize metrics if needed
        if tool_id not in self.metrics:
            self.metrics[tool_id] = ToolMetrics(tool_name=tool.manifest.name)
        
        metrics = self.metrics[tool_id]
        metrics.executions += 1
        
        start_time = time.time()
        
        try:
            result = tool.execute(params)
            metrics.successes += 1
            
            return {
                "success": True,
                "result": result,
                "tool_id": tool_id
            }
            
        except Exception as e:
            metrics.failures += 1
            metrics.errors.append(str(e))
            
            return {
                "success": False,
                "error": str(e),
                "tool_id": tool_id
            }
        
        finally:
            # Record latency
            latency_ms = (time.time() - start_time) * 1000
            metrics.total_latency_ms += latency_ms
    
    def get_metrics(self, tool_id: str = None) -> Dict:
        """Get metrics for specific tool or all tools"""
        if tool_id:
            metrics = self.metrics.get(tool_id)
            if not metrics:
                return {}
            
            return {
                "tool_name": metrics.tool_name,
                "executions": metrics.executions,
                "success_rate": f"{metrics.success_rate:.2%}",
                "avg_latency_ms": f"{metrics.avg_latency_ms:.2f}",
                "recent_errors": metrics.errors[-5:]
            }
        else:
            return {
                tool_id: self.get_metrics(tool_id)
                for tool_id in self.metrics.keys()
            }
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.get_metrics()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

# Usage
registry = MonitoredToolRegistry()
registry.load_from_registry_file("./tools/registry.json")

# Execute tools
result1 = registry.execute_tool("com.acme.search-database", {
    "query": "red shirts",
    "limit": 10
})

result2 = registry.execute_tool("com.weather.get-forecast", {
    "location": "Paris",
    "days": 3
})

# View metrics
print(json.dumps(registry.get_metrics(), indent=2))

# Export metrics
registry.export_metrics("tool_metrics.json")
```

---

## Best Practices Summary

1. **Always validate inputs** before execution
2. **Handle errors gracefully** using recovery strategies
3. **Monitor tool performance** in production
4. **Use tool selection logic** to choose the right tool
5. **Cache results** when tools are idempotent
6. **Respect rate limits** defined in operations
7. **Test thoroughly** using contract tests
8. **Version carefully** to avoid breaking changes

---

For more examples, see the `/examples` directory.
