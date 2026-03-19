# Anthropic Prompt Engineering Documentation Index

**Source:** https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/  
**Ingestion Date:** 2026-03-19  
**Total Coverage:** 2,931 lines across 7 comprehensive guides  
**Format:** Markdown, optimized for RAG chunking (350 tokens/chunk, 50-token overlap)

## Quick Navigation

### 1. Overview (`anthropic_prompt_engineering_overview.md`)
**Size:** 185 lines | **Token estimate:** ~250  
**Use case:** Start here to understand core prompting philosophy

**Covers:**
- Core principles: clarity, structure, examples, decomposition
- Prompting techniques overview
- Best practices and common pitfalls
- Performance optimization
- Example good prompts

---

### 2. System Prompts (`anthropic_prompt_engineering_system-prompts.md`)
**Size:** 317 lines | **Token estimate:** ~430  
**Use case:** Setting up consistent behavior and role definitions

**Covers:**
- What system prompts are and how they work
- Role definition patterns (expert, analyzer, coder, writer, teacher)
- Behavior instruction formatting
- Output format specification
- Advanced patterns: chaining, conditional behavior, uncertainty expression
- System prompt testing and iteration
- 3 complete example implementations

---

### 3. XML Tags (`anthropic_prompt_engineering_xml-tags.md`)
**Size:** 386 lines | **Token estimate:** ~520  
**Use case:** Structuring complex information and multi-part instructions

**Covers:**
- Why XML improves Claude's comprehension
- Basic tag patterns (task, context, instructions, examples)
- Data structuring with hierarchies
- Specialized patterns (analysis, comparison, recipes)
- Conditional behavior definition
- Real-world templates (code review, research summary, data extraction)
- Best practices: descriptive names, logical nesting, consistency
- Common mistakes and fixes
- When to use XML vs. other formats

---

### 4. Prefilling (`anthropic_prompt_engineering_prefilling.md`)
**Size:** 480 lines | **Token estimate:** ~650  
**Use case:** Guiding output format and style before generation starts

**Covers:**
- What prefilling is and how it works
- Use cases: output format, tone setting, section direction, brevity/detail
- Detailed examples (structured analysis, code generation, JSON output)
- Advanced techniques: combining with instructions, multi-turn, code blocks
- Prefilling for different output types (lists, comparisons, guides, specs, narratives)
- Best practices and patterns
- Combining with few-shot and chain-of-thought
- Consistency maintenance
- When not to prefill

---

### 5. Chain of Thought (`anthropic_prompt_engineering_chain-of-thought.md`)
**Size:** 474 lines | **Token estimate:** ~640  
**Use case:** Improving accuracy on complex reasoning tasks

**Covers:**
- Why chain-of-thought works and when it helps most
- Basic implementation methods (direct request, structured prompting, system prompts)
- Advanced techniques: constrained CoT, targeted reasoning, verify-then-solve
- Real-world examples (math problems, coding, analysis, decisions)
- Problem-type specific patterns (logical, mathematical, code analysis, creative)
- Combining CoT with few-shot, XML tags, system prompts
- Best practices: matching complexity, specific reasoning, verification
- How to measure improvement
- Common patterns (detective, engineering, scientific, consultant)

---

### 6. Tool Use / Function Calling (`anthropic_prompt_engineering_tool-use.md`)
**Size:** 550 lines | **Token estimate:** ~740  
**Use case:** Integrating Claude with external APIs, databases, and computation

**Covers:**
- What tool use is and why it matters
- 5-step tool use workflow with code examples
- Effective tool definition (names, descriptions, input schemas)
- 4 common tool patterns (lookup, calculation, API, search)
- Tool handler implementation (basic and production-ready)
- Advanced patterns: multi-step, composition, conditional
- Best practices: necessary tools only, clear descriptions, error handling
- Security considerations (validation, permissions, rate limiting)
- Complete working implementation example
- Debugging and observability
- When to use tool use

---

### 7. Long Context (`anthropic_prompt_engineering_long-context.md`)
**Size:** 539 lines | **Token estimate:** ~730  
**Use case:** Processing large documents (200K token windows)

**Covers:**
- Understanding token limits and counts
- When to use long context (document analysis, code review, knowledge extraction, batch processing)
- Organization and best practices for long inputs
- 5 core strategies: full document, focused queries, multiple documents, incremental, reference-heavy
- Optimization techniques: remove noise, use markers, maintain formatting, add navigation
- Patterns for document analysis (extraction, detail finding, summarization, metrics)
- Code analysis patterns
- Conversation patterns (progressive refinement, multi-perspective)
- Combining with other techniques (CoT, few-shot, XML)
- Challenge/solution pairs (information loss, attention distribution, token budget, response quality)
- When NOT to use long context

---

## Integration Notes

### Chunking Strategy
Each file is designed to be chunked by the KB system at ~350 tokens per chunk with 50-token overlap, creating 60-80 total chunks across all 7 files.

### Cross-Referencing
- Overview provides foundation
- System Prompts and XML Tags often work together
- Prefilling complements all other techniques
- Chain-of-Thought applies to complex reasoning
- Tool Use extends Claude's capabilities
- Long Context enables large-scale applications

### Recommended Learning Path
1. Start with **Overview** to understand core concepts
2. Pick your use case:
   - **Behavior control** → System Prompts
   - **Structure complex tasks** → XML Tags
   - **Format guidance** → Prefilling
   - **Better reasoning** → Chain of Thought
   - **External integration** → Tool Use
   - **Scale to documents** → Long Context

### Complementary Resources
These docs are designed to work with:
- Anthropic API documentation (for implementation details)
- Claude models documentation (for model-specific capabilities)
- Google Prompt Engineering whitepaper (for academic foundations)
- Your application's specific requirements

---

## File Organization

```
knowledge_base/sources/web/
├── anthropic_prompt_engineering_overview.md
├── anthropic_prompt_engineering_system-prompts.md
├── anthropic_prompt_engineering_xml-tags.md
├── anthropic_prompt_engineering_prefilling.md
├── anthropic_prompt_engineering_chain-of-thought.md
├── anthropic_prompt_engineering_tool-use.md
├── anthropic_prompt_engineering_long-context.md
└── README_ANTHROPIC_DOCS.md (this file)
```

---

## Metrics

| Metric | Value |
|--------|-------|
| Total lines | 2,931 |
| Total size | ~100 KB raw markdown |
| Estimated chunks | 60-80 |
| Documents | 7 comprehensive guides |
| Code examples | 30+ |
| Real-world patterns | 50+ |
| Topics covered | All major Claude prompting techniques |

---

## Version Info

- **Created:** 2026-03-19
- **Based on:** Anthropic platform.claude.com documentation
- **Status:** Ready for KB ingestion
- **Maintenance:** Update if Anthropic docs are revised

---

**Prepared by:** Victra, Director of Data  
**For:** Immortalize Labs HF Knowledge Base
