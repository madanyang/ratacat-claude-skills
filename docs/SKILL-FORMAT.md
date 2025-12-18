# Claude Code Skill Format Reference

This document defines the structure and best practices for Claude Code skills.

## What Are Skills?

Skills are knowledge files that Claude Code **automatically discovers and uses** based on context. Unlike slash commands (which users invoke explicitly with `/command`), skills are **model-invoked** — Claude reads the skill's description and activates it when relevant to the user's request.

## File Structure

Each skill lives in its own directory:

```
skill-name/
├── SKILL.md              # Required - main skill file
├── reference.md          # Optional - detailed documentation
├── examples.md           # Optional - usage examples
├── scripts/              # Optional - helper scripts
│   └── helper.py
└── templates/            # Optional - templates
    └── template.txt
```

## SKILL.md Format

### Required: YAML Frontmatter

```yaml
---
name: skill-name
description: What this skill does. Use when [trigger conditions].
---
```

| Field | Rules | Max Length |
|-------|-------|-----------|
| `name` | Lowercase letters, numbers, hyphens only (kebab-case) | 64 chars |
| `description` | Must include BOTH what it does AND when to use it | 1024 chars |
| `allowed-tools` | Optional - comma-separated tool list | N/A |

### Optional: Tool Restrictions

```yaml
---
name: safe-reader
description: Read-only file analysis. Use when auditing or reviewing code.
allowed-tools: Read, Grep, Glob
---
```

### Body Content

After the frontmatter, include:

1. **Instructions** - Step-by-step guidance for Claude
2. **Key Concepts** - Important terms and definitions
3. **Procedures** - How to accomplish common tasks
4. **Examples** - Concrete usage examples
5. **Warnings** - Pitfalls to avoid

## Skill Locations

Three scopes, checked in order:

```
Project:   .claude/skills/skill-name/SKILL.md     # This project only
Personal:  ~/.claude/skills/skill-name/SKILL.md   # All your projects
Plugin:    plugin-root/skills/skill-name/SKILL.md # Via plugins
```

## The Description Field (Critical)

The `description` is how Claude discovers when to use a skill. It must be **specific** and include **trigger keywords**.

### Bad Examples

```yaml
# Too vague - Claude won't know when to use it
description: Helps with databases

# Missing trigger conditions
description: PostgreSQL optimization techniques
```

### Good Examples

```yaml
# Specific + trigger conditions
description: Expert knowledge on PostgreSQL 16 internals, query optimization,
  and performance tuning. Use when working with Postgres databases, writing
  SQL queries, optimizing performance, or debugging database issues.

# File type triggers
description: Extract text and tables from PDF files, fill forms, merge
  documents. Use when working with PDF files or when the user mentions
  PDFs, forms, or document extraction.

# Operation triggers
description: Generate clear git commit messages from staged changes.
  Use when committing code or writing commit messages.
```

### Trigger Keyword Categories

Include keywords the user would naturally mention:

- **File types**: `.pdf`, `.xlsx`, `spreadsheet`, `JSON`
- **Operations**: `extract`, `analyze`, `convert`, `optimize`
- **Technologies**: `PostgreSQL`, `React`, `Docker`
- **Problem domains**: `performance`, `security`, `testing`

## Complete Example

```yaml
---
name: postgres-query-expert
description: Expert knowledge on PostgreSQL query optimization, indexing
  strategies, and performance tuning. Use when writing SQL queries,
  debugging slow queries, designing indexes, or working with PostgreSQL.
---

# PostgreSQL Query Expert

## Query Optimization Checklist

1. Check EXPLAIN ANALYZE output
2. Look for sequential scans on large tables
3. Verify indexes exist for WHERE/JOIN columns
4. Check for index-only scan opportunities
5. Review JOIN order and methods

## Indexing Guidelines

### When to Create Indexes

- Columns in WHERE clauses (high selectivity)
- JOIN columns
- ORDER BY columns (if sorting large result sets)
- Columns used in aggregate functions with GROUP BY

### When NOT to Index

- Small tables (< 1000 rows)
- Columns with low cardinality
- Write-heavy tables where read performance isn't critical
- Columns rarely used in queries

## Common Anti-Patterns

### Functions on Indexed Columns

```sql
-- Bad: Can't use index on created_at
SELECT * FROM orders WHERE DATE(created_at) = '2024-01-01';

-- Good: Uses index
SELECT * FROM orders
WHERE created_at >= '2024-01-01'
  AND created_at < '2024-01-02';
```

### SELECT *

```sql
-- Bad: Fetches unnecessary data, prevents index-only scans
SELECT * FROM users WHERE status = 'active';

-- Good: Only fetch needed columns
SELECT id, name, email FROM users WHERE status = 'active';
```

## Useful Diagnostic Queries

### Find Missing Indexes

```sql
SELECT schemaname, relname, seq_scan, idx_scan,
       seq_scan - idx_scan AS too_many_seqs
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY too_many_seqs DESC;
```

### Find Unused Indexes

```sql
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND schemaname = 'public';
```
```

## Skills vs Slash Commands

| Aspect | Skills | Slash Commands |
|--------|--------|----------------|
| Invocation | Automatic (model decides) | Explicit (`/command`) |
| Discovery | Via description matching | User must know command |
| Structure | Directory with SKILL.md | Single .md file |
| Use case | Domain expertise, complex workflows | Quick templates, specific actions |

**Use Skills when:**
- Claude should discover automatically based on context
- Multiple files or scripts needed
- Complex domain knowledge
- Team needs standardized expertise

**Use Slash Commands when:**
- Users explicitly invoke with `/command-name`
- Simple, single-file prompts
- Quick templates or reminders

## Validation Checklist

When generating skills programmatically:

- [ ] `name`: lowercase, hyphens, numbers only (max 64 chars)
- [ ] `description`: includes triggers AND use cases (max 1024 chars)
- [ ] YAML frontmatter properly formatted (opening and closing `---`)
- [ ] Directory created at correct path
- [ ] SKILL.md file exists in skill directory
- [ ] All file paths use forward slashes
- [ ] Any referenced scripts have execute permissions
- [ ] Supporting files exist relative to SKILL.md
- [ ] No absolute paths in skill content
