# Anthropic Prompt Engineering: XML Tags

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/xml-tags

## Why Use XML Tags?

XML tags help structure information and make instructions clearer. Claude treats XML tags as meaningful structural markers, not just text. Using XML tags:
- Makes complex information more organized
- Helps Claude understand semantic meaning
- Reduces ambiguity
- Works especially well for multi-step instructions
- Scales well to complex prompts

## Basic XML Tag Patterns

### Document or Task Definition
```xml
<task>
Analyze the provided code for bugs and suggest improvements.
</task>
```

### Providing Context
```xml
<context>
The user is learning Python and is unfamiliar with advanced concepts.
Explanations should be beginner-friendly.
</context>
```

### Instructions
```xml
<instructions>
1. Read through the entire document
2. Identify key themes
3. Provide a summary
4. List implications
</instructions>
```

### Examples
```xml
<examples>
<example>
<input>How do I write a function?</input>
<output>A function is a reusable block of code. Here's a simple example:
def greet(name):
    return f"Hello, {name}!"
</output>
</example>
</examples>
```

## Using XML for Structured Data

### Providing Multiple Items
```xml
<documents>
<document id="1">
<title>Document A</title>
<content>The content of document A...</content>
</document>
<document id="2">
<title>Document B</title>
<content>The content of document B...</content>
</document>
</documents>
```

### Complex Queries with Multiple Parts
```xml
<query>
<primary_question>What are the main findings?</primary_question>
<follow_up>How do these findings compare to previous research?</follow_up>
<format>Provide structured output with sections</format>
<constraints>
<constraint>Use only the provided documents</constraint>
<constraint>Limit response to 500 words</constraint>
</constraints>
</query>
```

## Specialized XML Patterns

### Analysis Requests
```xml
<analysis>
<subject>The recent market downturn</subject>
<aspects>
<aspect>Causes and contributing factors</aspect>
<aspect>Impact on different sectors</aspect>
<aspect>Recovery timeline estimates</aspect>
</aspects>
<depth>Technical but accessible</depth>
</analysis>
```

### Comparison Requests
```xml
<comparison>
<item1>Python</item1>
<item2>JavaScript</item2>
<criteria>
<criterion>Ease of learning</criterion>
<criterion>Performance</criterion>
<criterion>Use cases</criterion>
<criterion>Community and libraries</criterion>
</criteria>
</comparison>
```

### Step-by-Step Instructions
```xml
<recipe>
<title>Debugging a Python Script</title>
<steps>
<step number="1">
<action>Identify the error message</action>
<details>Read the traceback carefully</details>
</step>
<step number="2">
<action>Locate the error in the code</action>
<details>Use the line number from the traceback</details>
</step>
<step number="3">
<action>Understand what went wrong</action>
<details>Trace variable values at that point</details>
</step>
<step number="4">
<action>Implement a fix</action>
<details>Make the minimal change needed</details>
</step>
<step number="5">
<action>Test the fix</action>
<details>Run the script again to verify</details>
</step>
</steps>
</recipe>
```

## XML in System Prompts

You can use XML in system prompts to define behavior:

```
You are a helpful assistant. Always structure your responses as follows:

<response>
<summary>1-2 sentence overview</summary>
<details>3-5 paragraphs of explanation</details>
<examples>2-3 practical examples</examples>
<conclusion>Key takeaways</conclusion>
</response>
```

Then when a user asks a question, Claude will naturally use this structure.

## XML for Conditional Logic

Define different behaviors based on input type:

```xml
<behavior>
<case condition="user asks for code">
<action>Provide clean, well-commented code</action>
<action>Include usage examples</action>
<action>Explain any complex logic</action>
</case>
<case condition="user asks for explanation">
<action>Use simple language</action>
<action>Include analogies or examples</action>
<action>Check for understanding</action>
</case>
<case condition="ambiguity exists">
<action>Ask clarifying questions</action>
<action>Don't assume intent</action>
</case>
</behavior>
```

## Real-World Examples

### Code Review Template
```xml
<code_review>
<code>
def calculate_average(numbers):
    sum = 0
    for num in numbers:
        sum = sum + num
    average = sum / len(numbers)
    return average
</code>
<review_criteria>
<criterion>Correctness</criterion>
<criterion>Pythonic style</criterion>
<criterion>Performance</criterion>
<criterion>Edge cases</criterion>
</review_criteria>
</code_review>
```

### Research Summary Request
```xml
<research_request>
<topic>Machine Learning in Finance</topic>
<scope>
<scope_item>Applications in fraud detection</scope_item>
<scope_item>Algorithmic trading systems</scope_item>
<scope_item>Risk assessment models</scope_item>
</scope>
<output_format>
<section>Overview</section>
<section>Current applications</section>
<section>Challenges and limitations</section>
<section>Future directions</section>
</output_format>
<audience>Technical professionals new to the field</audience>
</research_request>
```

### Data Extraction Template
```xml
<extraction_task>
<source_text>
{Insert text to extract from}
</source_text>
<fields>
<field>Company name</field>
<field>Founded year</field>
<field>Industry</field>
<field>Revenue</field>
<field>Number of employees</field>
<field>Key products</field>
</fields>
<output_format>JSON</output_format>
</extraction_task>
```

## Best Practices with XML Tags

### 1. Use Descriptive Tag Names
**Good:**
```xml
<primary_objective>Find the root cause of performance issues</primary_objective>
```

**Less clear:**
```xml
<x>Find the root cause of performance issues</x>
```

### 2. Nest Logically
Structure XML to reflect the logical structure of your task:
```xml
<task>
  <input>User query</input>
  <processing>
    <step>Analyze</step>
    <step>Evaluate</step>
  </processing>
  <output>Formatted response</output>
</task>
```

### 3. Keep Tags Consistent
Use the same tag names throughout your prompt for similar concepts

### 4. Don't Overuse
XML is helpful, but too many tags can make prompts verbose:
- 3-5 main sections: excellent
- 20+ tags: probably too much

### 5. Combine with Examples
Use XML structure for the prompt AND in examples:
```xml
<example>
<input>
<query>What is machine learning?</query>
<audience>Beginners</audience>
</input>
<expected_output>
<definition>Machine learning is...</definition>
<analogy>Think of it like...</analogy>
<example_use_case>For example...</example_use_case>
</expected_output>
</example>
```

## XML for Complex Multi-Turn Conversations

Structure prompts for conversations:

```xml
<conversation_guide>
<initial_system_message>
You are a friendly tutor teaching Python to beginners.
</initial_system_message>
<interaction_pattern>
<turn type="1">
<role>user</role>
<description>Asks a question about a Python concept</description>
</turn>
<turn type="2">
<role>assistant</role>
<description>Explains clearly with examples</description>
<output_structure>
<part>Simple explanation</part>
<part>Code example</part>
<part>Checking understanding with a question</part>
</output_structure>
</turn>
<turn type="3">
<role>user</role>
<description>Responds or asks follow-up</description>
</turn>
</interaction_pattern>
</conversation_guide>
```

## XML vs. Other Formatting

### When to Use XML
- Complex multi-part instructions
- Structured data with hierarchies
- Instructions that repeat patterns
- When you need to define behavior for multiple scenarios

### When Simpler Formatting Works
- Simple, straightforward tasks
- Single-part requests
- When markdown or bullet points suffice

Combination approach:
```
# Task Overview
General description in markdown

<detailed_instructions>
<step>Complex step 1</step>
<step>Complex step 2</step>
</detailed_instructions>

Key constraint: Only use provided sources
```

## Common Mistakes with XML

### Mistake 1: Forgetting to Close Tags
```xml
<!-- Wrong -->
<instruction>Do this thing
<next_instruction>Do another thing</next_instruction>

<!-- Right -->
<instruction>Do this thing</instruction>
<next_instruction>Do another thing</next_instruction>
```

### Mistake 2: Improper Nesting
```xml
<!-- Wrong -->
<outer>
  <inner>content
</outer>
</inner>

<!-- Right -->
<outer>
  <inner>content</inner>
</outer>
```

### Mistake 3: Using Special Characters Without Escaping
```xml
<!-- Wrong -->
<instruction>If x > 5, do this</instruction>

<!-- Right -->
<instruction>If x &gt; 5, do this</instruction>
```

Or just use CDATA:
```xml
<instruction><![CDATA[If x > 5, do this]]></instruction>
```
