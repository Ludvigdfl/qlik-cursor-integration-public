# Basic CLI for Qlik Cloud

## Set-up

### 1. Install Syntax Highlighting

1. Open Cursor
2. Go to **Extensions** (or press `Ctrl+Shift+X`)
3. Click the **...** menu → **Install from VSIX...**
4. Select: `qlik highlight/gimly81.qlik-0.5.0.vsix`
5. Restart Cursor

### 2. Install Filename Highlighting

Install VSCode Icons Theme (`vscode-icons-team.vscode-icons`) and activate it to display Qlik Sense icons for `.qvs` files.

### 3. Add to Environment Variables

* Put the root of the folder in a logical place - like  `C:\Users\<YOU>\AppData\Local\Programs\<ROOT>`
* Expose the `qlik` command by adding the absolute path for the `qlik.cmd` to your system environment variables - `C:\Users\<YOU>\AppData\Local\Programs\Qlik_DEV\qlik`
* This will expose `qlik.cmd` during runtime.

### 4. Set Environment Variables

Set the following system environment variables:

| Variable | Value |
|----------|-------|
| `_QLIK_API_KEY_` | API key generated from your Qlik Cloud tenant |
| `_QLIK_TENANT_URL_` | Your tenant URL (e.g. `https://tenant.us.qlikcloud.com`) |


### 5. Usage

> **Important:** Always run `qlik` from your **project folder**, not from the CLI install directory.

```bash
cd c:\users\projects\mynewproject

qlik help              # list available commands 1
qlik get "MyApp"       # download app script as .qvs files
qlik get_space "space name" # get all apps in space
qlik set "MyApp"       # validate & push changes back
qlik load "MyApp"      # reload the app (streams logs)
qlik pub "MyApp"       # publish to managed space
```

### 6. Claude Code Skills

Two skills in `.claude/skills/` extend Claude Code with Qlik-aware behaviour:

| Skill | Purpose |
|-------|---------|
| **qlik-cli** | Lets Claude invoke the CLI commands (`get`, `set`, `load`, `pub`, …) on your behalf and manage the full script workflow from within the conversation. |
| **qlik-conventions** | Enforces Qlik Sense script syntax, formatting, and best practices whenever Claude edits or creates `.qvs` files (aligned `as` columns, correct keywords, proper statement termination). |

These skills are **not** globally installed. To use them, copy the `.claude/skills/` folder into your project's `.claude/` directory.

