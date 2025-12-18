"""
Gemini API wrapper for book processing.
Uses google-genai SDK with Gemini 2.5 Pro/Flash.
"""

import os
import json
import re
from google import genai
from google.genai import types


def parse_json_response(text: str) -> any:
    """Parse JSON from LLM response, handling common issues."""
    text = text.strip()

    # Remove markdown code fencing
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON array or object
    array_match = re.search(r'\[[\s\S]*\]', text)
    if array_match:
        try:
            return json.loads(array_match.group())
        except json.JSONDecodeError:
            pass

    object_match = re.search(r'\{[\s\S]*\}', text)
    if object_match:
        try:
            return json.loads(object_match.group())
        except json.JSONDecodeError:
            pass

    # If all else fails, raise with helpful message
    raise ValueError(f"Could not parse JSON from response: {text[:200]}...")


def get_client():
    """Get Gemini client. Expects GEMINI_API_KEY env var."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)


def propose_skill_metadata(text: str, model: str = "gemini-2.5-flash") -> list[dict]:
    """
    Analyze book text and propose skill names and descriptions.
    Returns list of 3 options, each with {name, description, rationale}.
    """
    client = get_client()

    prompt = """Analyze this book and propose 3 different Claude Code skill options.

Claude Code skills are knowledge files that Claude automatically discovers based on the description.
The description MUST include both what the skill does AND when to use it (trigger conditions).

For each option, provide:
1. name: kebab-case skill name (lowercase, hyphens, max 64 chars)
2. description: What this skill does + when to use it (max 1024 chars)
   - Include specific trigger keywords users would mention
   - Be specific, not vague
3. rationale: Brief explanation of why this name/description works

Propose 3 options with different angles:
- Option 1: Broad/general (covers the whole book's domain)
- Option 2: Focused (emphasizes the book's unique value)
- Option 3: Practical (emphasizes hands-on tasks/operations)

Return ONLY valid JSON array, no markdown fencing:
[{"name": "...", "description": "...", "rationale": "..."}, ...]

Book text (first portion):
"""

    # Send beginning of book - usually has title, intro, TOC
    response = client.models.generate_content(
        model=model,
        contents=prompt + text[:100000],
        config=types.GenerateContentConfig(
            temperature=0.3,
        )
    )

    return parse_json_response(response.text)


def identify_chapters(text: str, model: str = "gemini-2.5-flash") -> list[dict]:
    """
    Send full book text to Gemini and get chapter breakdown.
    Returns list of {title, start_pos, end_pos} for each chapter.
    """
    client = get_client()

    # Truncate text and note the length
    max_chars = 500000
    truncated_text = text[:max_chars]

    prompt = f"""Analyze this book text and identify the main chapters (not front matter, bibliography, etc).

The text is {len(truncated_text):,} characters long.

For each MAIN chapter, provide:
1. title: The chapter title/name
2. start_pos: Approximate character position where this chapter starts (0 to {len(truncated_text)})
3. end_pos: Approximate character position where this chapter ends

Focus on substantive chapters, skip:
- Title pages, copyright, dedication
- Table of contents
- Bibliography/references sections
- Appendices (unless substantive)

Return ONLY valid JSON array, no markdown fencing:
[{{"title": "Chapter 1: Name", "start_pos": 1000, "end_pos": 15000}}, ...]

Book text:
{truncated_text}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
        )
    )

    return parse_json_response(response.text)


def extract_chapter_text(full_text: str, start_pos: int, end_pos: int) -> str:
    """Extract chapter text between character positions."""
    # Clamp positions to valid range
    start_pos = max(0, start_pos)
    end_pos = min(len(full_text), end_pos)

    if start_pos >= end_pos:
        raise ValueError(f"Invalid positions: start={start_pos}, end={end_pos}")

    return full_text[start_pos:end_pos]


def process_chapter(chapter_title: str, chapter_text: str, book_title: str,
                    model: str = "gemini-2.5-flash") -> dict:
    """
    Process a single chapter and extract key knowledge for a Claude skill.
    Returns structured knowledge dict.
    """
    client = get_client()

    prompt = f"""You are extracting knowledge from a book chapter to create a Claude Code skill.
The skill will help Claude assist users with tasks related to this subject matter.

Book: {book_title}
Chapter: {chapter_title}

Extract the following from this chapter:

1. key_concepts: List of important concepts, terms, and definitions
2. procedures: Step-by-step procedures or methodologies described
3. best_practices: Recommended approaches, patterns, or guidelines
4. warnings: Common pitfalls, anti-patterns, or things to avoid
5. examples: Concrete examples that illustrate concepts
6. reference_info: Facts, syntax, commands, or reference material worth remembering

Return ONLY valid JSON:
{{
  "chapter_title": "{chapter_title}",
  "key_concepts": [...],
  "procedures": [...],
  "best_practices": [...],
  "warnings": [...],
  "examples": [...],
  "reference_info": [...]
}}

Chapter text:
{chapter_text[:100000]}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )

    return parse_json_response(response.text)


def plan_skill(book_title: str, skill_name: str, skill_description: str,
               chapter_extracts: list[dict], model: str = "gemini-2.5-pro") -> dict:
    """
    Analyze chapter extracts and create a detailed plan for the skill.
    Returns a structured plan for what the skill should contain.
    """
    client = get_client()

    prompt = f"""You are planning the structure and content of a Claude Code skill.

Claude Code skills are knowledge files that Claude automatically discovers and uses based on context.
The skill must be practical, actionable, and help Claude assist users effectively.

Book: {book_title}
Skill name: {skill_name}
Skill description: {skill_description}

Review these chapter extracts and create a detailed plan for the skill:

{json.dumps(chapter_extracts, indent=2)}

Create a plan that specifies:

1. sections: List of sections the skill should have, with:
   - title: Section heading
   - purpose: What this section accomplishes
   - key_points: 3-5 bullet points of what to include
   - priority: "essential", "important", or "nice-to-have"

2. examples_to_include: Specific examples from the extracts that MUST be in the skill
   - Each should have: context, code_or_content, why_important

3. warnings_and_pitfalls: Critical mistakes/anti-patterns to highlight

4. quick_reference: Facts, syntax, or commands that should be easily scannable

5. description_keywords: Trigger words/phrases for the skill description
   (technologies, operations, file types, problem domains users would mention)

6. estimated_length: "short" (< 200 lines), "medium" (200-500), or "long" (500+)

7. supporting_files: Whether to recommend additional files (reference.md, examples.md, etc.)

Return ONLY valid JSON:
{{
  "sections": [...],
  "examples_to_include": [...],
  "warnings_and_pitfalls": [...],
  "quick_reference": [...],
  "description_keywords": [...],
  "estimated_length": "...",
  "supporting_files": [...]
}}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )

    return parse_json_response(response.text)


def generate_skill(book_title: str, skill_name: str, skill_description: str,
                   chapter_extracts: list[dict], skill_plan: dict,
                   model: str = "gemini-2.5-pro") -> str:
    """
    Generate the final SKILL.md based on the plan.
    """
    client = get_client()

    prompt = f"""You are generating a Claude Code skill file (SKILL.md).

## Skill Format Requirements

The file MUST start with YAML frontmatter:
```yaml
---
name: {skill_name}
description: {skill_description}
---
```

After frontmatter, include markdown content with:
- Clear section headers (##, ###)
- Bullet points for scannability
- Code blocks with language tags
- Concrete examples
- Warnings/pitfalls clearly marked

## Context

Book: {book_title}
Skill name: {skill_name}

## The Plan to Follow

{json.dumps(skill_plan, indent=2)}

## Source Material (Chapter Extracts)

{json.dumps(chapter_extracts, indent=2)}

## Instructions

Generate the complete SKILL.md file following the plan above.

Key principles:
1. Be DENSE with useful information - every line should add value
2. Prioritize actionable guidance over theory
3. Include ALL the examples marked in the plan
4. Make warnings/pitfalls prominent
5. Quick reference sections should be scannable (tables, short bullets)
6. Use code blocks with proper language tags
7. No fluff or filler content

Generate the SKILL.md now:
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=16384,
        )
    )

    return response.text


# Keep the old function for backwards compatibility, but have it use the new two-step process
def synthesize_skill(book_title: str, skill_name: str, skill_description: str,
                     chapter_extracts: list[dict], model: str = "gemini-2.5-pro") -> str:
    """
    Take all chapter extracts and synthesize into a comprehensive SKILL.md.
    Uses two-step process: plan then generate.
    """
    plan = plan_skill(book_title, skill_name, skill_description, chapter_extracts, model)
    return generate_skill(book_title, skill_name, skill_description, chapter_extracts, plan, model)
