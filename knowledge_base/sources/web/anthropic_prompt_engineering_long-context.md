# Anthropic Prompt Engineering: Long Context Handling

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/long-context

## What is Long Context?

Long context refers to Claude's ability to process large amounts of input text — up to 200,000 tokens for Claude 3.5 Sonnet. This enables:
- Analyzing entire documents, books, or code repositories
- Processing large datasets
- Maintaining conversation history
- Working with extensive context windows

## Token Limits by Model

| Model | Context Window |
|-------|-----------------|
| Claude 3.5 Sonnet | 200,000 tokens |
| Claude 3 Opus | 200,000 tokens |
| Claude 3 Sonnet | 200,000 tokens |
| Claude 3 Haiku | 200,000 tokens |

## Understanding Token Count

Tokens are roughly:
- 4 characters ≈ 1 token
- 1 word ≈ 1.3 tokens
- A page of text ≈ 250-300 tokens

**Example:**
```
A 200-page book ≈ 50,000-60,000 tokens
So Claude can process multiple books in a single request
```

## When to Use Long Context

### Ideal Use Cases

1. **Document Analysis**
   - Analyze entire reports, papers, or books
   - Compare multiple documents
   - Extract information from large texts

2. **Code Review**
   - Review entire codebase files or modules
   - Understand code context without summary
   - Maintain full project context

3. **Knowledge Extraction**
   - Extract structured information from documents
   - Build summaries with complete context
   - Answer questions about document details

4. **Conversation Context**
   - Keep conversation history for continuity
   - Maintain context over many turns
   - Reference earlier parts of conversation

5. **Batch Processing**
   - Process multiple items at once
   - Apply same analysis to different documents
   - Compare patterns across documents

## Best Practices for Long Context

### 1. Organize Information Clearly
Structure long documents for clarity:

```
Document Title: [Title]
Source: [Source/URL]
Date: [Date]

---

# Section 1: Introduction
[Content]

# Section 2: Main Content
[Content]

# Section 3: Conclusion
[Content]
```

### 2. Use Markers for Important Sections
Help Claude navigate the document:

```
===== START OF IMPORTANT SECTION =====
[Critical information]
===== END OF IMPORTANT SECTION =====
```

### 3. Include a Summary for Navigation
Help Claude understand document structure:

```
DOCUMENT OVERVIEW:
- Pages 1-5: Introduction
- Pages 6-20: Technical Details
- Pages 21-30: Results
- Pages 31-40: Conclusions

Full Document:
[Complete content]
```

### 4. Break Down Complex Analysis Tasks
For large documents, specify exactly what you want:

```
Analyze the following 50-page report for:
1. Key findings (main results)
2. Methodology (how they did the research)
3. Implications (what it means)
4. Limitations (caveats and issues)

Report:
[Full report text]
```

### 5. Ask Specific Questions
Rather than open-ended requests:

**Vague:**
```
What do you think about this document?
[50-page document]
```

**Better:**
```
In the following document, please identify:
1. The primary research question
2. The main findings
3. Any contradictions with prior research
4. Recommendations for future work

[Document]
```

## Long Context Strategies

### Strategy 1: Full Document + Analysis
Provide entire document with specific analysis requests:

```
Analyze the attached financial report for:
- Revenue trends
- Expense patterns
- Profitability
- Cash flow insights

Financial Report:
[Complete report]
```

### Strategy 2: Document + Focused Queries
Include document but ask targeted questions:

```
Question 1: What are the primary risks mentioned?
Question 2: What metrics are used to measure success?
Question 3: Are there any contradictions?

Document:
[Complete document]
```

### Strategy 3: Multiple Documents
Analyze and compare several documents:

```
Compare the following three reports:

Document 1: Annual Report 2023
[Full text]

Document 2: Quarterly Report Q4 2023
[Full text]

Document 3: Market Analysis 2024
[Full text]

Comparison: Identify major differences
```

### Strategy 4: Incremental Context
Build context gradually over conversation:

```
Turn 1: Provide document
User: What are the main points?
Claude: [Summary based on full document]

Turn 2: 
User: Tell me more about Section 3
Claude: [Uses full context to elaborate]

Turn 3:
User: How does this compare to X?
Claude: [Uses full context for comparison]
```

### Strategy 5: Reference-Heavy Analysis
When you need multiple references:

```
In the following documents, find connections:

Document A: [Paper 1]
Document B: [Paper 2]
Document C: [Paper 3]
Document D: [Paper 4]

Task: Identify how findings in Document A are supported or contradicted by B, C, and D.
```

## Optimizing for Long Context

### 1. Remove Unnecessary Content
Clean up documents before processing:

**Include:**
- Relevant text
- Headers and structure
- Key data

**Remove:**
- Boilerplate content
- Repeated headers
- Irrelevant metadata
- Excessive formatting

### 2. Use Clear Section Markers
Make structure obvious:

```
<section id="executive-summary">
[Summary content]
</section>

<section id="methodology">
[Methods content]
</section>
```

### 3. Maintain Consistent Formatting
Consistent structure helps comprehension:

```
# Title

## Introduction
[Content]

## Methods
[Content]

## Results
[Content]
```

### 4. Use Natural Language References
Help Claude navigate:

```
As mentioned in the Introduction section...
As shown in Figure 3 (page 15)...
In the Methodology section...
```

### 5. Provide Navigation Aids
Include tables of contents or outlines:

```
DOCUMENT STRUCTURE:
1. Executive Summary (p. 1-2)
2. Background (p. 3-10)
3. Key Findings (p. 11-25)
4. Analysis (p. 26-35)
5. Recommendations (p. 36-40)

[Full document follows]
```

## Analyzing Large Documents Effectively

### Pattern 1: Extract Information
```
Extract the following from the document:
- Company name
- Founded year
- Current market position
- Growth strategy
- Key challenges

Document: [Full text]
```

### Pattern 2: Find Specific Details
```
Find all instances where the document discusses:
1. Technical challenges
2. Cost implications
3. Timeline estimates

Document: [Full text]
```

### Pattern 3: Summarize Sections
```
Provide summaries of these sections:
1. Executive Summary - 2 sentences
2. Technical Details - 3 sentences
3. Conclusions - 2 sentences

Document: [Full text]
```

### Pattern 4: Identify Key Metrics
```
Extract and organize all metrics/numbers mentioned:
- What is measured?
- What is the value?
- What is the context?

Document: [Full text]
```

### Pattern 5: Synthesize Multiple Documents
```
These four documents discuss the same topic from different angles:

Document 1: [Paper A]
Document 2: [Paper B]
Document 3: [Paper C]
Document 4: [Paper D]

Synthesize: What are the common themes? Where do they disagree?
```

## Managing Token Usage with Long Context

### Calculate Token Count
Estimate tokens before sending:

```python
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")
text = open("document.txt").read()
tokens = len(enc.encode(text))
print(f"Tokens: {tokens}")  # Usually: len(text) / 4
```

### Optimize Token Efficiency
- Remove unnecessary content
- Use compression where possible
- Focus requests on key sections
- Break into multiple requests if needed

### Token-Efficient Querying
```
Instead of:
"What do you think of this 100-page document?"

Use:
"In this document, identify: 1) Key claims 2) Evidence provided 3) Potential weaknesses"
```

## Long Context for Code Analysis

### Entire Function Analysis
```
Analyze this complete module for:
1. Security vulnerabilities
2. Performance issues
3. Code style compliance
4. Test coverage needs

Code:
[Full module code]
```

### Cross-File Analysis
```
These files are part of the same system:

auth.py:
[Full code]

database.py:
[Full code]

user.py:
[Full code]

Analysis: Are there any integration issues between these modules?
```

### Repository Analysis
```
This is the core module of our project:

[Entire src/ directory contents]

Questions:
1. What is the main data flow?
2. Are there architectural issues?
3. What refactoring would help?
```

## Long Context Conversation Patterns

### Pattern 1: Progressive Refinement
```
Turn 1: 
User: Analyze this document
Claude: [High-level analysis of full document]

Turn 2:
User: Go deeper into section 3
Claude: [Detailed analysis using full context]

Turn 3:
User: Compare section 3 to section 7
Claude: [Comparison using full context]
```

### Pattern 2: Multi-Perspective Analysis
```
Turn 1:
User: Here's a business proposal [document]
Claude: [Analysis from business perspective]

Turn 2:
User: Analyze from a technical perspective
Claude: [Uses full document for technical analysis]

Turn 3:
User: Analyze from a risk perspective
Claude: [Uses full document for risk analysis]
```

## Combining Long Context with Other Techniques

### Long Context + Chain of Thought
```
Document: [100-page report]

Before answering, think through:
1. What are the document's main claims?
2. What evidence supports them?
3. Are there counterarguments?
4. What conclusions are justified?

Then answer: Are the conclusions well-supported?
```

### Long Context + Few-Shot Examples
```
Example 1: Good analysis [short example]
Example 2: Good analysis [short example]

Document: [Full document]

Now analyze: Using the style of the examples, analyze this document.
```

### Long Context + XML Structure
```xml
<task>
<document>
[Full document text]
</document>
<analysis>
<aspect>Financial health</aspect>
<aspect>Growth potential</aspect>
<aspect>Risk factors</aspect>
</analysis>
</task>
```

## Common Challenges and Solutions

### Challenge 1: Information Loss
**Problem:** Claude might miss details in very long documents
**Solution:** 
- Ask specific questions
- Use markers for important sections
- Provide multiple passes with different queries

### Challenge 2: Attention Distribution
**Problem:** Model might weight early content more heavily
**Solution:**
- Put critical information in clear sections
- Use explicit markers for important parts
- Ask focused questions

### Challenge 3: Token Budget
**Problem:** Long documents consume tokens quickly
**Solution:**
- Remove unnecessary content
- Be specific in your requests
- Use multiple API calls for different aspects

### Challenge 4: Response Quality
**Problem:** Responses might be superficial with very long inputs
**Solution:**
- Ask for specific depth levels
- Request structured output
- Use chain-of-thought reasoning

## When NOT to Use Long Context

Don't use long context if:
- You need real-time updates (documents change frequently)
- Your document is poorly structured or very dense
- You're doing simple lookups (just need one fact)
- You have extensive context but ask vague questions

In these cases:
- Use search/retrieval first, then provide relevant excerpts
- Break documents into smaller pieces
- Ask specific, focused questions
- Consider preprocessing the document

## Best Practices Summary

1. **Organize documents clearly** with headers and sections
2. **Ask specific questions** rather than general ones
3. **Use markers** for important or repeated content
4. **Calculate token usage** before sending
5. **Optimize content** by removing unnecessary material
6. **Combine techniques** (long context + chain of thought)
7. **Test and iterate** to find optimal structure
8. **Verify accuracy** especially for critical information
