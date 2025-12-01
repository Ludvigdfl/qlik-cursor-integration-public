# Qlik Sense Script Analysis Prompt

## Overview
Analyze all Qlik Sense script files (`.qvs` files) in the provided context and generate a structured, concise explanation of the script's functionality.

---

## Step 1: Read & Analyze
- Identify all `.qvs` files in the provided folder/context
- Read and understand each script file
- Note file dependencies and execution order

---

## Step 2: Generate Analysis

Create a structured analysis document following this template:

### 📋 Required Sections

#### 1. Summary
**What to include:**
- Overall objective of the script collection
- High-level description of main functionality (2-3 sentences)
- Core purpose without field-level detail

#### 2. Data Read From
**What to include:**
- External files (Excel, CSV, databases, etc.)
- Connection strings or file paths
- Data source types (QVD, QVX, REST APIs, etc.)
- Any failed or missing data sources

**Format:**
- List each source with type and location
- Note status (successful, failed, missing)
- Keep at table/source level, not field level

#### 3. Data Created
**What to include:**
- Table names created in the script 
- Purpose/description of each table
- Source method (LOAD, AUTOGENERATE, JOIN, etc.)
- Keep at table level, not field level

**Format:**
- List each table with its purpose
- Note how it's created (from which source or transformation)

---

## Step 3: Formatting Guidelines

### Structure
- Use clear headings and subheadings
- Use bullet points for lists
- Keep paragraphs short (2-3 sentences max)

### Conciseness
- Focus on essential information only
- Avoid redundant explanations
- Skip field-level details
- Keep at table/source level only

### Visual Hierarchy
- Use markdown formatting (bold, italics, code blocks)
- Separate sections clearly
- Use horizontal rules (`---`) between major sections

---

## Output Template

```markdown
# Qlik Sense Script Analysis

## Summary
[2-3 sentence overview of main functionality]

## Data Read From
- [Source 1]: [Type] - [Location/Path] - [Status]
- [Source 2]: [Type] - [Location/Path] - [Status]

## Data Created
- **[TableName1]**: [Purpose/Description] - Created from [Source/Method]
- **[TableName2]**: [Purpose/Description] - Created from [Source/Method]
```

---

## Files to Analyze
**Scope**: All `.qvs` files in the provided folder/context.
