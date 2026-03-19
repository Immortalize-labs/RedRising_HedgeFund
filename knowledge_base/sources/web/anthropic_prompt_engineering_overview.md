# Anthropic Prompt Engineering: Overview

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/

## Introduction

Prompt engineering is the art of writing clear, structured instructions to get the best results from Claude. Unlike traditional programming where you compile and execute code, prompt engineering relies on clear communication with a language model. The quality of your results depends directly on how well you communicate your requirements.

## Core Principles

### 1. Be Clear and Explicit

Give Claude as much context as you can. Include:
- The task you want to accomplish
- The format of the desired output
- The domain or context
- Any constraints or requirements

### 2. Use Structured Formats

Structure makes information easier to process. Use:
- Numbered lists for sequential steps
- Bullet points for related items
- Sections with clear headings
- XML tags for important information

### 3. Provide Examples

Examples help Claude understand patterns:
- Few-shot learning: provide 1-3 examples of inputs and expected outputs
- Shows the style, format, and reasoning you want
- More effective than describing the task in abstract terms

### 4. Break Down Complex Tasks

Decompose hard problems:
- Chain of thought: ask Claude to reason through steps
- Divide large tasks into smaller subtasks
- Use multi-turn conversations to build on previous outputs

## Prompt Engineering Techniques

### System Prompts
A system prompt is an instruction given to Claude before the conversation starts. It sets the tone, role, and behavior for the entire conversation.

**Example:**
```
You are a helpful, harmless, and honest assistant. You always provide accurate information and acknowledge when you're uncertain.
```

### Few-Shot Prompting
Provide examples of the task in action:
```
Input: "The cat sat on the mat"
Output: "The cat (noun), sat (verb), on (preposition), the mat (article+noun)"

Input: "I love programming"
Output: "I (pronoun), love (verb), programming (noun)"
```

### Chain of Thought
Ask Claude to reason through the problem step-by-step before answering:
```
Before answering, think through:
1. What is the main question?
2. What relevant information do I have?
3. What steps do I need to take?
4. What is my final answer?
```

### Structured Output
Request output in a specific format:
```
Return the answer as JSON:
{
  "answer": "...",
  "confidence": 0-100,
  "reasoning": "..."
}
```

## Best Practices

### 1. Clarity Over Length
Longer prompts aren't always better. Focus on:
- Clear requirement statements
- Relevant context only
- Concise examples

### 2. Role Assignment
Tell Claude what role to play:
- "You are a Python expert..."
- "As a financial analyst..."
- "Acting as a technical reviewer..."

### 3. Constraints and Rules
Explicitly state constraints:
- "Do not use external libraries"
- "Keep the response under 100 words"
- "Use only the provided documents as sources"

### 4. Test and Iterate
- Start with simple prompts
- Add complexity based on results
- Keep versions of prompts that work well

## Common Pitfalls

### 1. Ambiguous Instructions
**Bad:** "Summarize the document"
**Better:** "Write a 2-3 sentence summary of the key findings in simple language"

### 2. Missing Context
Always provide relevant background information and any specific requirements

### 3. Vague Output Expectations
Don't assume Claude knows your format needs. Be explicit about:
- Structure (JSON, Markdown, bullet points, etc.)
- Length constraints
- Tone and style
- Special instructions

## Performance Tips

### 1. Token Efficiency
- Use concise language where possible
- Remove redundant information
- Reference documents rather than copying all content

### 2. Temperature and Sampling
Different tasks need different creativity levels:
- Tasks requiring precision: lower temperature
- Creative tasks: higher temperature

### 3. Model Selection
- Use Claude 3 Opus for complex reasoning
- Use Claude 3 Sonnet for balanced performance
- Use Claude 3 Haiku for speed and cost

## Examples of Good Prompts

### Task: Code Review
```
Review the following Python function for:
1. Correctness - does it solve the stated problem?
2. Style - does it follow PEP 8?
3. Efficiency - are there performance issues?
4. Safety - are there security concerns?

Provide feedback as:
- Issues found (if any)
- Suggested improvements (if any)
- Overall assessment
```

### Task: Information Extraction
```
Extract the following information from the document:
- Company name
- Founded year
- Number of employees
- Industry
- Key products

Return as JSON.
```

### Task: Creative Writing
```
Write a short story (300 words) about:
- Setting: A futuristic city
- Character: An AI that questions its purpose
- Tone: Contemplative and philosophical
- Audience: Science fiction readers
```

## Next Steps

The following sections dive deeper into specific techniques:
- System prompts and how to use them effectively
- XML tags for structured information
- Prefilling for direct response guidance
- Chain of thought prompting
- Tool use and function calling
- Long context handling and retrieval
