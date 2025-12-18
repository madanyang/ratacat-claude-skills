"""
Gemini API wrapper for book processing.
Uses google-genai SDK with Gemini 2.5 Pro/Flash.
"""

import os
import json
from google import genai
from google.genai import types


def get_client():
    """Get Gemini client. Expects GEMINI_API_KEY env var."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)


def identify_chapters(text: str, model: str = "gemini-2.5-flash-preview-05-06") -> list[dict]:
    """
    Send full book text to Gemini and get chapter breakdown.
    Returns list of {title, start_marker, end_marker} for each chapter.
    """
    client = get_client()

    prompt = """Analyze this book text and identify all chapters or major sections.

For each chapter, provide:
1. title: The chapter title/name
2. start_marker: A unique phrase (10-20 words) that marks where this chapter begins
3. end_marker: A unique phrase (10-20 words) that marks where this chapter ends

Return ONLY valid JSON array, no markdown fencing:
[{"title": "...", "start_marker": "...", "end_marker": "..."}, ...]

Book text:
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt + text[:500000],  # Gemini has large context, but be reasonable
        config=types.GenerateContentConfig(
            temperature=0.1,  # Low temp for structured output
        )
    )

    # Parse JSON from response
    response_text = response.text.strip()
    # Handle potential markdown fencing
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    return json.loads(response_text)


def extract_chapter_text(full_text: str, start_marker: str, end_marker: str) -> str:
    """Extract chapter text between markers."""
    start_idx = full_text.find(start_marker)
    end_idx = full_text.find(end_marker)

    if start_idx == -1:
        raise ValueError(f"Start marker not found: {start_marker[:50]}...")
    if end_idx == -1:
        # If no end marker, take to end of text
        return full_text[start_idx:]

    return full_text[start_idx:end_idx + len(end_marker)]


def process_chapter(chapter_title: str, chapter_text: str, book_title: str,
                    model: str = "gemini-2.5-flash-preview-05-06") -> dict:
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

    response_text = response.text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    return json.loads(response_text)


def synthesize_skill(book_title: str, skill_name: str, skill_description: str,
                     chapter_extracts: list[dict], model: str = "gemini-2.5-pro-preview-05-06") -> str:
    """
    Take all chapter extracts and synthesize into a comprehensive SKILL.md.
    Uses Pro model for this final synthesis step.
    """
    client = get_client()

    prompt = f"""You are creating a Claude Code skill from extracted book knowledge.

Book: {book_title}
Skill name: {skill_name}
Skill description: {skill_description}

Create a comprehensive SKILL.md file that will help Claude assist users with this subject matter.
The skill should be practical, actionable, and dense with useful information.

Requirements:
1. Start with YAML frontmatter:
   ---
   name: {skill_name}
   description: {skill_description}
   ---

2. Organize the content logically with clear sections
3. Include concrete examples and code snippets where applicable
4. Prioritize actionable guidance over theory
5. Include common pitfalls and how to avoid them
6. Make it scannable with good headers and bullet points

Chapter extracts to synthesize:
{json.dumps(chapter_extracts, indent=2)}

Generate the complete SKILL.md content:
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=8192,
        )
    )

    return response.text
