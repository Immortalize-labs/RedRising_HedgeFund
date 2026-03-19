# Anthropic Prompt Engineering: Chain of Thought

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/chain-of-thought

## What is Chain of Thought?

Chain of Thought (CoT) is a prompting technique where you explicitly ask Claude to reason through a problem step-by-step before providing a final answer. Instead of jumping to conclusions, Claude explains its reasoning process, which typically improves the quality and accuracy of responses.

## Why Chain of Thought Works

Research shows that step-by-step reasoning helps:
- **Accuracy:** Models make fewer mistakes when they show their work
- **Complex problems:** Breaking problems into steps makes them more manageable
- **Verification:** You can check the reasoning to understand any errors
- **Transparency:** You see HOW Claude arrived at the answer
- **Multi-step reasoning:** Problems involving multiple operations benefit significantly

## Basic Chain of Thought Pattern

Ask Claude to think through the problem before answering:

**Without Chain of Thought:**
```
Q: If a store has 12 items and sells 3 per day for 4 days, how many remain?
A: 0 items
```

**With Chain of Thought:**
```
Q: If a store has 12 items and sells 3 per day for 4 days, how many remain?
Think through this step-by-step.

A: Let me work through this:
1. Starting items: 12
2. Items sold per day: 3
3. Number of days: 4
4. Total items sold: 3 × 4 = 12 items
5. Items remaining: 12 - 12 = 0 items
```

## Implementation Methods

### Method 1: Direct Request
Simply ask Claude to think step-by-step:

```
Problem: [Your problem]
Before answering, please think through this step-by-step.
```

### Method 2: Structured Prompting
Provide a specific structure:

```
Please solve this problem using the following structure:

1. Problem Statement: Restate the problem
2. Key Information: What do we know?
3. Relevant Concepts: What principles apply?
4. Solution Steps: Work through it
5. Final Answer: State the conclusion
```

### Method 3: System Prompt Instruction
Include in your system prompt:

```
Always think through problems systematically.
Before providing an answer, explain:
1. What you understand from the problem
2. What approach you'll take
3. Your step-by-step reasoning
4. Your final conclusion
```

### Method 4: Explicit Reasoning Sections
Use markers to separate reasoning from answers:

```
Problem: [problem]

<thinking>
[Claude's reasoning]
</thinking>

<answer>
[Claude's final answer]
</answer>
```

## Advanced Chain of Thought Techniques

### Technique 1: Constrained Chain of Thought

Limit the reasoning to prevent excessive verbosity:

```
Problem: [your problem]

Think through this step-by-step, but be concise.
Limit your reasoning to 3-5 key steps.
```

### Technique 2: Chain of Thought with Examples

Demonstrate the reasoning style you want:

```
Example problem: "If Bob has 5 apples and receives 3 more, how many does he have?"
Reasoning example: 
- Starting apples: 5
- Additional apples: 3
- Total: 5 + 3 = 8 apples
- Answer: 8 apples

Now solve: [Your problem]
Reasoning:
```

### Technique 3: Targeted Reasoning

Ask for reasoning on specific aspects:

```
Problem: Should we invest in this company?

Please reason through:
1. Financial health: [your reasoning]
2. Market position: [your reasoning]
3. Growth potential: [your reasoning]
4. Risks: [your reasoning]

Final recommendation:
```

### Technique 4: Verify-Then-Solve

Ask Claude to verify understanding before solving:

```
Problem: [complex problem]

Before solving:
1. Confirm what you understand the problem to be
2. Identify any assumptions you're making
3. Then provide your solution step-by-step
```

## Real-World Examples

### Example 1: Mathematical Problem

**Prompt:**
```
Solve this step-by-step:
A train leaves city A traveling at 60 mph.
A second train leaves city B (120 miles away) traveling at 80 mph.
When do they meet?

Think through:
1. What are we trying to find?
2. What's the setup?
3. How do we approach this?
4. Work through the math
5. Verify the answer
```

### Example 2: Coding Problem

**Prompt:**
```
I need to debug this Python function:

def find_duplicates(lst):
    return [x for x in lst if lst.count(x) > 1]

Before telling me the issues, think through:
1. What is this function trying to do?
2. Test it mentally with examples
3. Identify any problems
4. Explain each issue
5. Suggest a better approach
```

### Example 3: Analytical Question

**Prompt:**
```
Question: Why might a company fail despite having a great product?

Please think through:
1. What factors beyond product quality matter?
2. Market-related factors:
3. Execution-related factors:
4. Timing-related factors:
5. How these interact
6. Summary of key reasons
```

### Example 4: Decision Making

**Prompt:**
```
Should we hire this candidate?

Candidate: [details]

Reasoning process:
1. Required skills check: [your analysis]
2. Experience assessment: [your analysis]
3. Culture fit: [your analysis]
4. Growth potential: [your analysis]
5. Risk factors: [your analysis]
6. Recommendation with justification:
```

## Chain of Thought for Different Problem Types

### For Logical Reasoning
```
Use this structure:
1. State the given facts
2. Identify what we need to prove
3. List relevant rules or principles
4. Apply each rule to the facts
5. Draw conclusions
```

### For Math Problems
```
Use this structure:
1. Identify what we're solving for
2. List known quantities
3. Identify relevant formulas
4. Substitute values
5. Calculate step-by-step
6. Verify the answer
```

### For Code Analysis
```
Use this structure:
1. Describe what the code should do
2. Trace through with an example
3. Identify unexpected behavior
4. Explain the root cause
5. Suggest corrections
```

### For Creative Work
```
Use this structure:
1. Understand the requirements
2. Brainstorm ideas
3. Evaluate each idea against requirements
4. Combine strongest elements
5. Refine the result
```

## Combining Chain of Thought with Other Techniques

### Chain of Thought + Few-Shot Learning
```
Example 1:
Question: [example Q]
Reasoning: [example reasoning]
Answer: [example answer]

Example 2:
Question: [example Q]
Reasoning: [example reasoning]
Answer: [example answer]

Now your question: [user question]
Reasoning:
```

### Chain of Thought + XML Tags
```xml
<problem>
[Your problem]
</problem>

<reasoning>
<step1>Understanding: </step1>
<step2>Analysis: </step2>
<step3>Calculation: </step3>
</reasoning>

<answer></answer>
```

### Chain of Thought + System Prompts
```
System: You are a logical thinker who reasons systematically.
Always show your work step-by-step before providing an answer.

User: [problem]
```

## Chain of Thought Best Practices

### 1. Match Complexity to Problem
**Simple problem:**
```
What's 2+2? 
```
No need for extensive reasoning.

**Complex problem:**
```
Analyze the pros and cons of remote work...
Think through this systematically.
```

### 2. Be Specific About What to Reason Through
**Vague:**
```
Think about this problem
```

**Better:**
```
Before answering, think through:
1. The key assumptions
2. Potential alternative interpretations
3. Each approach and its trade-offs
```

### 3. Use Clear Delimiters
Help separate thinking from answering:

```
<thinking>
[show work here]
</thinking>

<answer>
[final answer]
</answer>
```

### 4. Validate Reasoning
Ask Claude to check its own work:

```
Now that you've reasoned through this, 
verify your answer by working backwards.
```

### 5. Adjust Verbosity
Control how detailed the reasoning should be:

```
Think through this concisely in 2-3 sentences of reasoning.
```

vs.

```
Provide comprehensive step-by-step reasoning.
```

## Chain of Thought for Complex Multi-Step Problems

For problems requiring many steps, structure the reasoning:

```
Problem: [complex problem]

Break this into phases:

Phase 1: Understanding
- What is the goal?
- What constraints exist?
- What assumptions are we making?

Phase 2: Analysis
- What information is relevant?
- What's the relationship between components?
- What patterns do we see?

Phase 3: Solution
- What approach makes sense?
- Work through each step
- Verify the logic

Phase 4: Validation
- Does this answer the original question?
- Are there edge cases to consider?
- Is the solution reasonable?
```

## When Chain of Thought Helps Most

Chain of Thought is particularly beneficial for:
- Multi-step math problems
- Logic puzzles
- Code debugging
- Complex reasoning
- Novel problem-solving
- Risk analysis
- Decision-making with trade-offs

It provides less benefit for:
- Factual questions (dates, definitions)
- Simple retrieval tasks
- Opinion-based questions where consensus exists
- Creative tasks where reasoning might constrain creativity

## Measuring Improvement

You can measure how much Chain of Thought helps:

```python
# Without reasoning
response1 = client.messages.create(...)

# With reasoning
response2 = client.messages.create(
    messages=[
        ...,
        {"role": "assistant", "content": "Let me think through this..."}
    ]
)

# Compare accuracy/quality
```

## Common Chain of Thought Patterns

### The Detective Pattern
```
Given: [facts]

Step 1: Gather information
Step 2: Identify clues
Step 3: Form hypotheses
Step 4: Test hypotheses
Step 5: Draw conclusions
```

### The Engineering Pattern
```
Requirements: [what needs to be done]

1. Requirements analysis
2. Design phase
3. Implementation phase
4. Testing phase
5. Deployment considerations
```

### The Scientific Pattern
```
Hypothesis: [proposed explanation]

1. Review existing knowledge
2. Design an experiment
3. Make predictions
4. Analyze results
5. Draw conclusions
```

### The Consultant Pattern
```
Situation: [business problem]

1. Problem diagnosis
2. Root cause analysis
3. Option generation
4. Evaluation of options
5. Recommendation
```
