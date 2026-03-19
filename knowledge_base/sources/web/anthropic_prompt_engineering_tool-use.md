# Anthropic Prompt Engineering: Tool Use / Function Calling

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/tool-use

## What is Tool Use?

Tool use (also called function calling) allows Claude to call external functions, APIs, or tools to accomplish tasks. Instead of Claude only generating text, it can:
- Call functions and use their results
- Query databases
- Fetch real-time information
- Perform calculations
- Integrate with external services

## Why Tool Use Matters

Tool use extends Claude beyond text generation:
- **Real-time data:** Access current information
- **Accuracy:** Use specialized tools instead of relying on training data
- **Automation:** Integrate Claude with your systems
- **Complex workflows:** Chain multiple operations
- **Grounding:** Ground responses in actual data

## How Tool Use Works

### Step 1: Define Tools
Tell Claude what tools are available:

```python
tools = [
    {
        "name": "calculate",
        "description": "Perform mathematical calculations",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    }
]
```

### Step 2: Claude Recognizes When Tools Are Needed
When Claude determines a tool would help, it requests the tool:

```
User: What's the square root of 144?

Claude response:
I'll calculate the square root of 144 for you.
<tool_use id="1" name="calculate">
<input>
<expression>sqrt(144)</expression>
</input>
</tool_use>
```

### Step 3: You Execute the Tool
Your application catches the tool request and executes it:

```python
if tool_use.name == "calculate":
    result = eval(tool_use.input["expression"])
```

### Step 4: Return Results to Claude
Provide the tool result back to Claude:

```python
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "1",
            "content": "144"
        }
    ]
})
```

### Step 5: Claude Provides Final Answer
Claude uses the tool result to answer the user:

```
Claude: The square root of 144 is 12.
```

## Defining Tools Effectively

### Tool Definition Structure
```python
{
    "name": "tool_name",              # Unique identifier
    "description": "What this tool does",  # Clear description
    "input_schema": {                 # JSON Schema for inputs
        "type": "object",
        "properties": {
            "parameter_name": {
                "type": "string",
                "description": "What this parameter does"
            }
        },
        "required": ["parameter_name"]
    }
}
```

### Best Practices for Tool Definitions

#### 1. Clear Names and Descriptions
**Good:**
```python
{
    "name": "get_weather",
    "description": "Get current weather conditions for a specified location",
    ...
}
```

**Poor:**
```python
{
    "name": "wx",
    "description": "Get info",
    ...
}
```

#### 2. Specific Parameter Descriptions
**Good:**
```python
"parameters": {
    "location": {
        "type": "string",
        "description": "City name (e.g., 'San Francisco') or coordinates (e.g., '37.7749,-122.4194')"
    }
}
```

**Poor:**
```python
"parameters": {
    "loc": {
        "type": "string",
        "description": "location"
    }
}
```

#### 3. Constrain Parameter Types
Use appropriate JSON Schema types:

```python
{
    "name": "search_products",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_price": {
                "type": "number",
                "description": "Maximum price filter"
            },
            "in_stock_only": {
                "type": "boolean",
                "description": "Only show in-stock items"
            },
            "category": {
                "type": "string",
                "enum": ["electronics", "clothing", "books"],
                "description": "Product category"
            }
        },
        "required": ["query"]
    }
}
```

## Common Tool Patterns

### Pattern 1: Data Lookup Tools
```python
{
    "name": "lookup_user",
    "description": "Look up user information by ID or email",
    "input_schema": {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "User ID or email address"
            }
        },
        "required": ["user_id"]
    }
}
```

### Pattern 2: Calculation Tools
```python
{
    "name": "calculate_loan_payment",
    "description": "Calculate monthly loan payments",
    "input_schema": {
        "type": "object",
        "properties": {
            "principal": {
                "type": "number",
                "description": "Loan amount"
            },
            "annual_rate": {
                "type": "number",
                "description": "Annual interest rate (e.g., 5.5 for 5.5%)"
            },
            "months": {
                "type": "number",
                "description": "Loan term in months"
            }
        },
        "required": ["principal", "annual_rate", "months"]
    }
}
```

### Pattern 3: API Integration Tools
```python
{
    "name": "fetch_exchange_rate",
    "description": "Get current exchange rate between two currencies",
    "input_schema": {
        "type": "object",
        "properties": {
            "from_currency": {
                "type": "string",
                "description": "Source currency code (e.g., 'USD')"
            },
            "to_currency": {
                "type": "string",
                "description": "Target currency code (e.g., 'EUR')"
            }
        },
        "required": ["from_currency", "to_currency"]
    }
}
```

### Pattern 4: Search Tools
```python
{
    "name": "search_documentation",
    "description": "Search through product documentation",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keywords"
            },
            "section": {
                "type": "string",
                "enum": ["api", "guides", "faq", "troubleshooting"],
                "description": "Documentation section to search in"
            }
        },
        "required": ["query"]
    }
}
```

## Implementing Tool Handlers

### Basic Handler
```python
def handle_tool_call(tool_name, tool_input):
    if tool_name == "calculate":
        result = eval(tool_input["expression"])
        return str(result)
    elif tool_name == "get_weather":
        location = tool_input["location"]
        # Call weather API
        return fetch_weather(location)
    else:
        return f"Unknown tool: {tool_name}"
```

### Production Handler with Error Handling
```python
def handle_tool_call(tool_name, tool_input):
    try:
        if tool_name == "database_query":
            return execute_query(tool_input["sql"])
        elif tool_name == "api_call":
            return call_external_api(tool_input["endpoint"])
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}
```

## Advanced Tool Use Patterns

### Multi-Step Tool Use
Claude can call multiple tools in sequence:

```
User: Compare prices for flights to Paris and hotels in Paris

Claude:
1. Calls search_flights(destination="Paris")
2. Calls search_hotels(location="Paris")
3. Processes results and provides comparison
```

### Tool Composition
Chain tools together for complex workflows:

```python
tools = [
    "get_user_data",
    "query_database",
    "calculate_metrics",
    "format_report"
]

# Claude might call: get_user_data → query_database → 
# calculate_metrics → format_report
```

### Conditional Tool Use
Different tools based on context:

```python
tools = [
    {
        "name": "search_web",
        "description": "For current information"
    },
    {
        "name": "query_documents",
        "description": "For internal documents"
    }
]

# Claude chooses appropriate tool based on user request
```

## Best Practices for Tool Use

### 1. Only Include Necessary Tools
Fewer, focused tools work better:

**Better:**
```python
tools = [
    "search_products",
    "place_order",
    "check_status"
]
```

**Worse:**
```python
tools = [
    "search_products",
    "search_services",
    "search_anything",
    "place_order",
    "cancel_order",
    "modify_order",
    "check_status",
    ...
]
```

### 2. Provide Clear Descriptions
Claude decides when to use tools based on descriptions:

```python
{
    "name": "check_inventory",
    "description": "Check if a product is in stock and get inventory count"
    # This tells Claude WHEN to use this tool
}
```

### 3. Handle Errors Gracefully
Tools may fail; handle this appropriately:

```python
{
    "type": "tool_result",
    "tool_use_id": "123",
    "content": "Error: Invalid product ID",
    "is_error": True  # Mark as error
}
```

### 4. Use Tool Results Naturally
Let Claude incorporate tool results into its response:

```
Claude: Based on the current inventory levels, 
we have 45 units of the product in stock.
```

### 5. Optimize for Latency
Tool calls add latency; balance functionality with speed

## Tool Use Security Considerations

### Input Validation
Always validate tool inputs before execution:

```python
def search_database(query):
    # Validate that query is safe
    if not is_safe_query(query):
        return {"error": "Invalid query"}
    return execute_query(query)
```

### Permission Checks
Ensure the user has permission to use the tool:

```python
def delete_file(file_id):
    if not user_has_permission("delete", file_id):
        return {"error": "Permission denied"}
    return delete_file_impl(file_id)
```

### Rate Limiting
Prevent abuse of tool calling:

```python
def apply_rate_limit(user_id, tool_name):
    calls_this_minute = get_call_count(user_id, tool_name)
    if calls_this_minute > MAX_CALLS_PER_MINUTE:
        return {"error": "Rate limit exceeded"}
```

## Example: Complete Tool Use Implementation

```python
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "calculator",
        "description": "Perform mathematical calculations",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression"
                }
            },
            "required": ["expression"]
        }
    }
]

def process_tool_call(tool_name, tool_input):
    if tool_name == "calculator":
        return str(eval(tool_input["expression"]))
    return "Unknown tool"

messages = [
    {"role": "user", "content": "What is 25 * 4 + 100?"}
]

while True:
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    
    if response.stop_reason == "tool_use":
        for block in response.content:
            if block.type == "tool_use":
                result = process_tool_call(block.name, block.input)
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        }
                    ]
                })
    else:
        break

print(response.content[-1].text)
```

## Debugging Tool Use

### Check if Tool is Being Called
```python
print(f"Stop reason: {response.stop_reason}")
# Should be "tool_use" if Claude calls a tool
```

### Inspect Tool Requests
```python
for block in response.content:
    if block.type == "tool_use":
        print(f"Tool: {block.name}")
        print(f"Input: {block.input}")
```

### Monitor Tool Results
```python
if result.get("error"):
    print(f"Tool error: {result['error']}")
```

## When to Use Tool Use

Tool use is valuable for:
- Real-time information (weather, stock prices, news)
- System integration (databases, APIs, file systems)
- Complex calculations
- Data transformation
- Automated workflows

Tool use is less necessary for:
- Pure text generation
- Tasks within Claude's training data
- One-off analytical questions
- Tasks that don't require external information
