# Qlik Script cli   

## Set-up

### 1. Expose 'qlik' as a cli

* Put the root of the folder in a logical place - like  `C:\Users\<YOU>\AppData\Local\Programs\<ROOT>`
* Expose the `qlik` command by adding the absolute path for the `qlik.cmd` to your system environment variables - `C:\Users\<YOU>\AppData\Local\Programs\Qlik_DEV\qlik`
* This will expose `qlik.cmd` during runtime.

### 2. Connect to a Qlik Cloud Tenant

```bash
qlik set_tenant https://{tenant}.{region}.qlikcloud.com
qlik set_tenant_api_key <your-api-key>
qlik get_tenant   # get current tenant URL and API key
```

### 3. Usage

> **Important:** Always run `qlik` from your **project folder**, not from the CLI install directory from step 1.

```bash
cd c:\users\projects\mynewproject

qlik help                        # list available commands

qlik get "MyApp"                 # download app script as .qvs files
qlik get_space "space name"      # get all apps in space
qlik set "MyApp"                 # validate & push changes back
qlik load "MyApp"                # reload the app (streams logs)
qlik pub "MyApp"                 # publish to managed space
qlik rem "MyApp"                 # delete local script directory

qlik get_ms "MyApp"              # download master measures → Apps/{id}/{name}/masteritems/measures.json
qlik set_ms "MyApp"              # create/update master measures from measures.json
qlik get_dim "MyApp"             # download master dimensions → Apps/{id}/{name}/masteritems/dimensions.json
qlik set_dim "MyApp"             # create/update master dimensions from dimensions.json

qlik set_tenant <url>            # set Qlik tenant URL
qlik set_tenant_api_key <key>    # set Qlik API key
qlik get_tenant                  # show current tenant URL and API key
```

### 4. Master Items (Measures & Dimensions)

Master items are stored as JSON files alongside the app's script tabs under `Apps/{appId}/{appName}/masteritems/`.

**Typical workflow:**

```bash
# Pull current master items from the app into local JSON files
qlik get_ms "MyApp"              # → masteritems/measures.json
qlik get_dim "MyApp"             # → masteritems/dimensions.json

# Edit measures.json / dimensions.json locally, then push back
qlik set_ms "MyApp"              # create or update measures in the app
qlik set_dim "MyApp"             # create or update dimensions in the app
```

**JSON schema — measures.json**

```json
[
  {
    "id":          "abc123",
    "title":       "Total Sales",
    "definition":  "Sum(Sales)",
    "label":       "='Total Sales'",
    "description": "Sum of all sales",
    "fmt":         "#,##0.00",
    "tags":        ["finance"]
  }
]
```

**JSON schema — dimensions.json**

```json
[
  {
    "id":               "def456",
    "title":            "Customer",
    "definition":       "CustomerName",
    "label":            "Customer",
    "label_expression": "='Customer'",
    "description":      "Customer name dimension",
    "tags":             ["crm"]
  }
]
```

> **Duplicate handling:** if the app contains more than one master item with the same title, `set_ms` / `set_dim` will skip that item and write the conflicting entries to `measures_duplicates.json` / `dimensions_duplicates.json` for manual review.

### 5. Claude Code Skills

Two skills in `.claude/skills/` extend Claude Code with Qlik-aware behaviour:

| Skill | Purpose |
|-------|---------|
| **qlik-cli** | Lets Claude invoke the CLI commands (`get`, `set`, `load`, `pub`, `set_tenant`, `get_tenant`, …) on your behalf and manage the full script workflow from within the conversation. |
| **qlik-conventions** | Enforces Qlik Sense script syntax, formatting, and best practices whenever Claude edits or creates `.qvs` files (aligned `as` columns, correct keywords, proper statement termination). Feel free to extend this according to your own preferences.|

Skills can also be globally installed in `~/.claude/skills/` to be available in any project.

### 6. Install Syntax Highlighting

1. Open Cursor
2. Go to **Extensions** (or press `Ctrl+Shift+X`)
3. Click the **...** menu → **Install from VSIX...**
4. Select: `qlik highlight/gimly81.qlik-0.5.0.vsix`
5. Restart Cursor

### 7. Install Filename Highlighting

Install VSCode Icons Theme (`vscode-icons-team.vscode-icons`) and activate it to display Qlik Sense icons for `.qvs` files.
