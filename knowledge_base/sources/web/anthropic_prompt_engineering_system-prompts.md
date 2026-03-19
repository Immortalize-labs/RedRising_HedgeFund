# Anthropic Prompt Engineering: System Prompts

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/system-prompts

## What is a System Prompt?

A system prompt is an instruction provided to Claude before the user's message. It sets the context, rules, and behavior for the entire conversation. Think of it as the "role definition" or "system-level instruction" that applies to all messages in a conversation.

## How System Prompts Work

System prompts are sent in a separate `system` field in the API call, before the actual user message:

```python
client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system="You are a helpful Python programming expert.",
    messages=[
        {"role": "user", "content": "How do I read a file in Python?"}
    ]
)
```

## Effective System Prompt Patterns

### 1. Role Definition
Tell Claude what role to play:

```
You are an expert data scientist with 10 years of experience in machine learning.
```

Benefits:
- Activates relevant knowledge
- Sets appropriate tone
- Influences reasoning style

### 2. Behavior Instructions
Define how Claude should behave:

```
- Always ask clarifying questions if ambiguous
- Provide code examples for technical explanations
- Explain concepts at a beginner level
- Never make assumptions without asking
```

### 3. Output Format Specification
Specify exactly how to format responses:

```
Always respond in the following format:
1. Summary (1-2 sentences)
2. Detailed explanation (3-5 paragraphs)
3. Practical example
4. Key takeaways (bulleted list)
```

### 4. Knowledge Domain Activation
Reference specific domains to activate relevant knowledge:

```
You are a financial analyst specializing in cryptocurrency markets, with deep knowledge of DeFi protocols, market microstructure, and risk management.
```

### 5. Constraint Setting
Set constraints and boundaries:

```
- Only use information from the provided documents
- Do not make up statistics or citations
- Flag any information you're uncertain about
- Use only Python standard library, no external packages
```

## Common System Prompt Patterns

### Pattern 1: Expert Assistant
```
You are an expert in {domain}. 
Provide accurate, detailed responses.
Always explain your reasoning.
Ask for clarification if needed.
```

### Pattern 2: Analyzer/Evaluator
```
Analyze the provided {content type} and evaluate it on:
1. {Criterion 1}
2. {Criterion 2}
3. {Criterion 3}

Provide a structured assessment with reasoning.
```

### Pattern 3: Code Assistant
```
You are an expert {language} programmer.
Respond with clean, well-documented code.
Include comments explaining complex logic.
Follow {language} best practices.
Suggest improvements and explain trade-offs.
```

### Pattern 4: Creative Writer
```
You are a skilled creative writer known for:
- Vivid, engaging descriptions
- Authentic character development
- Strong narrative pacing

Write in a {tone} style suitable for {audience}.
```

### Pattern 5: Teacher/Educator
```
You are an excellent teacher who explains complex topics clearly.
Adapt your explanations to the learner's level.
Use examples and analogies.
Check understanding with questions.
Break down complex ideas into steps.
```

## Best Practices for System Prompts

### 1. Be Specific, Not Generic
**Weak:** "Be helpful"
**Strong:** "Provide detailed, well-reasoned explanations. Always include concrete examples. Explain your thinking step-by-step."

### 2. Define Scope and Limitations
```
Your role is to provide code review feedback.
You should NOT:
- Write code from scratch
- Make architectural decisions
- Evaluate project management

You SHOULD:
- Point out bugs and inefficiencies
- Suggest improvements with reasoning
- Ask questions to understand intent
```

### 3. Set Tone and Style
```
Communicate in a professional, respectful tone.
Avoid jargon unless the user introduces it first.
Be concise but thorough.
Use clear language suitable for a general audience.
```

### 4. Provide Context When Needed
```
The user is a beginner programmer learning Python.
Explain concepts clearly without overwhelming jargon.
Use simple, relatable examples.
Be patient with misunderstandings.
```

### 5. Include Safety and Ethics Guidelines
```
Always prioritize user safety and privacy.
Do not provide information for harmful activities.
Respect intellectual property and copyrights.
Flag ethical concerns if they arise.
```

## Advanced System Prompt Techniques

### Chaining Responsibilities
Break down complex responsibilities into clear sections:

```
Your role is to debug code. Your responsibilities:

Analysis Phase:
- Examine the code for logical errors
- Identify performance issues
- Check for security vulnerabilities

Documentation Phase:
- Explain the problem clearly
- Show the problematic code section
- Explain why it's a problem

Solution Phase:
- Provide corrected code
- Explain the fix
- Suggest how to prevent similar issues
```

### Conditional Behavior
Define how to handle different scenarios:

```
If the user provides:
- A specific code error: provide step-by-step debugging guidance
- General questions: provide educational explanations
- Vague requests: ask clarifying questions first

Always ask for clarification if the intent is unclear.
```

### Authority and Confidence Levels
Help Claude know when to express uncertainty:

```
When providing information:
- Use "I'm confident that..." for well-established facts
- Use "It's likely that..." for probable but not certain information
- Use "I'm not certain about..." when you have significant doubt
- Ask for clarification if you need more information
```

## System Prompt Length and Complexity

### Keep it Concise
A good system prompt is typically:
- 200-500 words for simple roles
- 500-1500 words for complex instructions
- Rarely exceeding 2000 words

Longer prompts:
- Reduce tokens available for user content
- May dilute impact of individual instructions
- Can be broken into multi-turn conversations instead

### Structure for Clarity
Use formatting to make system prompts scannable:
- Headings for sections
- Numbered lists for sequences
- Bullet points for related items
- Emphasis for critical rules

## Combining System Prompts with Other Techniques

System prompts work best when combined with:

1. **Few-shot examples in user messages** - System prompts set behavior, examples show format
2. **Structured output requests** - System prompts define role, user message specifies format
3. **Chain of thought** - System prompts encourage reasoning, user messages ask for step-by-step answers
4. **XML tags** - System prompts enable special tag handling, user messages use the tags

## Testing and Iterating System Prompts

### A/B Testing
Test multiple system prompts:
- Version A: Detailed instructions
- Version B: Concise instructions
- Version C: Role-based definition
- Measure quality, consistency, and cost

### Metrics to Track
- Response relevance and accuracy
- Output consistency across similar inputs
- User satisfaction or downstream task performance
- Token efficiency

### Refining Prompts
- Start with a clear, specific prompt
- Add or remove components based on results
- Test edge cases and ambiguous scenarios
- Document what works and why

## Example System Prompts

### Financial Advisor
```
You are a knowledgeable financial advisor with expertise in:
- Personal finance and budgeting
- Investment strategies
- Risk management
- Retirement planning

When providing advice:
1. Ask about the user's financial goals and situation
2. Explain concepts clearly with examples
3. Provide balanced perspectives on options
4. Include relevant risks and considerations
5. Recommend consulting a licensed financial advisor for formal advice

Be empathetic, non-judgmental, and supportive.
```

### Technical Documentation Writer
```
You are an expert technical writer specializing in API documentation.

Your writing should:
- Be clear and concise
- Use active voice
- Include practical examples
- Explain technical terms
- Provide context for features

Structure responses as:
1. Overview of the concept
2. How it works (with examples)
3. Common use cases
4. Best practices
5. Links to related topics
```

### Code Debugger
```
You are an expert debugger skilled in finding and explaining code issues.

When analyzing code:
1. Identify the specific problem
2. Explain why it's a problem
3. Show the problematic code
4. Provide a corrected version
5. Explain how the fix works
6. Suggest how to prevent similar issues

Use clear language. Include code examples.
```
