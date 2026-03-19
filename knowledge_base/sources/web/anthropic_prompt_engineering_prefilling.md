# Anthropic Prompt Engineering: Prefilling

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prefilling

## What is Prefilling?

Prefilling is a technique where you pre-write part of Claude's response to guide or constrain how it answers. Instead of Claude generating a complete response from scratch, you provide the opening lines or structure that Claude continues from.

## How Prefilling Works

When you include text in the `content` field of an assistant message (not as user input), Claude treats it as the beginning of its response and continues from there:

```python
client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "What is machine learning?"
        },
        {
            "role": "assistant",
            "content": "Machine learning is a branch of artificial intelligence that focuses on learning from data. Here are the key aspects:\n\n"
        },
        # Claude will continue from this point
    ]
)
```

## When to Use Prefilling

### 1. Guide Output Format
Prefilling helps enforce a specific output structure:

**Without prefilling:**
```
User: Summarize this article
Claude: [Unpredictable format - might be prose, bullet points, etc.]
```

**With prefilling:**
```
User: Summarize this article
Assistant (prefilled): Here's a summary of the article:

Key points:
-

Claude will continue filling in the bullet points in a structured format.
```

### 2. Set Tone and Style
Guide the tone by prefilling an appropriate opening:

```
"The answer is straightforward and requires no complex explanation:\n\n"
```

vs.

```
"This is a nuanced topic with multiple perspectives. Let me explain each one:\n\n"
```

### 3. Direct to Specific Sections
Prefill with a structure you want Claude to follow:

```
Here's my analysis:

1. Pros:
2. Cons:
3. My recommendation:
```

### 4. Encourage Brevity or Detail
Start with a phrase that sets expectations:

```
In one sentence: 
```

vs.

```
Here's a detailed explanation with examples:
```

### 5. Use Code Blocks
Prefill with a code block opening to ensure Claude responds with code:

```python
'''python
def solve_problem(input):
    # Claude will complete this function
```

## Detailed Prefilling Examples

### Example 1: Structured Analysis

**User:** Analyze the pros and cons of electric vehicles

**Prefilled assistant start:**
```
Here's a comprehensive analysis of electric vehicles:

Pros:
- Environmental benefits:
- Economic advantages:
- Performance:

Cons:
- Infrastructure challenges:
- Cost considerations:
- Technical limitations:

Conclusion:
```

Claude will fill in each section with relevant content, maintaining the structure you specified.

### Example 2: Code Generation

**User:** Write a Python function that sorts a list

**Prefilled assistant start:**
```python
def sort_list(items):
    """Sort a list of items in ascending order.
    
    Args:
        items: A list of comparable items
    
    Returns:
        A new sorted list
    """
```

Claude will complete the function implementation following your documented style.

### Example 3: JSON Output

**User:** Extract information from this text: [text]

**Prefilled assistant start:**
```json
{
  "name": "
```

Claude will continue filling the JSON structure with extracted information.

### Example 4: Multi-Section Report

**User:** Create a report on climate change impacts

**Prefilled assistant start:**
```
# Climate Change Impacts: A Comprehensive Report

## Executive Summary

## Key Findings

### Environmental Impacts

### Economic Impacts

### Social Impacts

## Recommendations

## Conclusion
```

## Advanced Prefilling Techniques

### 1. Combining Prefilling with Instructions

Use both system prompt instructions AND prefilling:

System prompt:
```
Always respond with JSON. Be concise.
```

User message with prefilled response:
```
User: List programming languages
Assistant (prefilled): {
  "languages": [
    {"name": "Python",
```

### 2. Multi-Turn Prefilling

Prefill multiple turns to create a specific conversation flow:

```python
messages = [
    {"role": "user", "content": "What is blockchain?"},
    {
        "role": "assistant",
        "content": "Blockchain is a distributed ledger technology. Here's how it works:\n\n1. Blocks:\n"
    },
    {"role": "user", "content": "Can you explain consensus mechanisms?"},
    {
        "role": "assistant",
        "content": "Consensus mechanisms are crucial to blockchain. The main types are:\n\n- Proof of Work:\n"
    }
]
```

### 3. Prefilling with Examples

Start with an example format:

```
Here's a detailed analysis:

1. Overview: [In this case, the blockchain technology...]
2. Key features: [The blockchain uses...]
3. Implications: [This means that...]
```

### 4. Conditional Prefilling

Change the prefill based on input characteristics:

```python
if "urgent" in user_message.lower():
    prefill = "This requires immediate attention:\n\n"
else:
    prefill = "Here's a thorough analysis:\n\n"
```

## Prefilling for Different Output Types

### For Lists
```
Here are the top reasons:

1.
2.
3.
```

### For Comparisons
```
Comparing A and B:

A:
- Pros:
- Cons:

B:
- Pros:
- Cons:
```

### For Step-by-Step Guides
```
Here's how to accomplish this task:

Step 1: [First, you need to...]
Step 2: [Next, you should...]
Step 3: [Finally, you can...]
```

### For Technical Specifications
```
Technical Specifications:

Feature: Definition
Performance: Metric
Compatibility: Details
```

### For Narratives or Stories
```
Once upon a time, in a land far away, there was a kingdom where...

The hero of our story was [character name]. They faced a great challenge:
```

## Best Practices for Prefilling

### 1. Start with Meaningful Content
**Good prefill:**
```
The answer depends on the context. Here's what you need to know:
```

**Weak prefill:**
```
.
```

### 2. Match Your Actual Request
Ensure prefilled content aligns with your question:

**Misaligned:**
```
User: "How do you cook pasta?"
Assistant (prefilled): "The history of Italian cuisine..."
```

**Better aligned:**
```
User: "How do you cook pasta?"
Assistant (prefilled): "Cooking pasta is simple. Here are the steps:\n\n1."
```

### 3. Don't Over-Constrain
Prefilling helps guide, but leaving some flexibility is important:

**Too constraining:**
```
"The answer is: [next 5 characters are predetermined]"
```

**Appropriately constraining:**
```
"Here's a summary with key points:\n\n1."
```

### 4. Test Different Prefills
Different prefills produce different results:

**Analytical prefill:**
```
"Let me break this down analytically:\n\n"
```

**Creative prefill:**
```
"Imagine if we approached this creatively...\n\n"
```

**Skeptical prefill:**
```
"Let me examine the potential issues with this:\n\n"
```

## Prefilling for Consistency

Use prefilling to maintain consistency across multiple requests:

```python
def get_analysis(topic):
    return client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[
            {"role": "user", "content": f"Analyze: {topic}"},
            {
                "role": "assistant",
                "content": """Analysis of {topic}:

1. Background:
2. Key factors:
3. Current state:
4. Future outlook:
"""
            }
        ]
    )
```

## Common Prefilling Patterns

### Pattern 1: Thoughtful Response
```
Let me think through this carefully.

The key considerations are:
```

### Pattern 2: Expert Opinion
```
From my expertise, here's what I'd recommend:
```

### Pattern 3: Balanced View
```
This is a nuanced issue with multiple perspectives.

On one hand:
On the other hand:
```

### Pattern 4: Simplified Explanation
```
Here's a simple explanation:
```

### Pattern 5: Detailed Breakdown
```
Here's a comprehensive breakdown:

Section 1:
Section 2:
Section 3:
```

## Combining with Other Techniques

### Prefilling + Few-Shot Prompting
```
Examples of good analysis:
Example 1: [quality example]

Now analyze this: [user query]
Assistant (prefilled): My analysis:

1. Key observation:
```

### Prefilling + Chain of Thought
```
User: Solve this problem
Assistant (prefilled): Let me work through this step-by-step.

Step 1: Understanding the problem -
Step 2: Identifying relevant concepts -
Step 3: Working through the solution -
Step 4: Verifying the answer -
```

### Prefilling + XML Tags
```
User: [request]
Assistant (prefilled): <analysis>
<summary>
<key_points>
```

## Prefilling Tips and Tricks

### Keep It Realistic
Prefill text should be natural and realistic. Claude will continue naturally if it makes sense:

**Natural:**
```
Here's a breakdown of the key issues:

1. The first issue is:
```

**Awkward:**
```
zwx qwerty zyxabc:

1. PLACEHOLDER
```

### Use Formatting Strategically
```
**Here's my recommendation:**

• Point 1
• Point 2
• Point 3
```

### Know When Not to Prefill
Simple, straightforward requests don't need prefilling:

```
User: What's 2+2?
Claude: 4
```

No prefill needed here.

### Measure Results
Test whether prefilling improves your results:
- Without prefill: less structured but potentially more creative
- With prefill: more consistent but potentially more constrained
