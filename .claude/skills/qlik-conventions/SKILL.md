---
name: qlik-conventions
description: Enforces Qlik Sense script syntax, formatting, and best practices when editing or creating .qvs files. Use when working with any .qvs file, Qlik load scripts, or Qlik script expressions. Triggers on Qlik script editing, .qvs file creation, or any Qlik data model work.
---

# Qlik Script Conventions

## Syntax Rules

- Use ONLY Qlik Sense script syntax in `.qvs` files - never SQL, Python, or other languages.
- Terminate all statements with `;`
- Use Qlik keywords: `Load`, `From`, `Where`, `Join`, `Resident`, etc.
- Use Qlik functions: `Chr()`, `RecNo()`, `Pick()`, `Round()`, `Rand()`, etc.
- Name tables with a trailing colon: `TableName:`

## Formatting Rules

- Indent all statements within a block at the same width.
- **Align all `as` keywords** at the same column position in Load statements, regardless of field name/expression length.

### Correct formatting example

```qlik
Load
    'long string value'    as DATA,
    short                  as DATA2,
    today()                as DATE,
    malmö                  as CITY
From
    [lib://DataSource/data.qvd](qvd)
;
```

### Incorrect syntax (never use)

```sql
-- SQL: DO NOT USE
SELECT * FROM table WHERE condition;
-- Python: DO NOT USE
import pandas; df = pd.read_csv()
```
