---
name: qlik-cli
description: Custom CLI for managing Qlik Sense Cloud app scripts, reloads, and publishing. Use when the user asks to get, edit, set, reload, or publish Qlik app scripts, or when working with .qvs files in the scripts/ directory. Triggers on references to Qlik apps, Qlik scripts, reload tasks, master items (measures/dimensions), or the "qlik" command.
---

# Qlik CLI

Custom CLI at `qlik/qlik.cmd` for managing Qlik Sense Cloud apps via the REST API.

## Prerequisites

Tenant URL and API key are stored in `.qlik_config.json` in the project root (gitignored). Configure them once with:

```
qlik set_tenant <tenant_url>
qlik set_tenant_api_key <api_key>
```

Values take effect immediately for all subsequent commands. As a fallback, the CLI also reads `_QLIK_TENANT_URL_` and `_QLIK_API_KEY_` environment variables if the config file is absent.

## Commands

Invoke via Bash: `PYTHONIOENCODING=utf-8 "$HOME/AppData/Local/Programs/Qlik_DEV/qlik/qlik.cmd" <command> <args>`

| Command | Usage | Description |
|---------|-------|-------------|
| `get_space` | `qlik get_space <space_name>` | Download script, master items, and sheet objects for all apps in a shared space |
| `get_app` | `qlik get_app <app_name> [<app_id>]` | Download script, master items, and sheet objects from a shared space app |
| `set_script` | `qlik set_script <app_name> [<app_id>]` | Validate and upload local .qvs files as app script |
| `load_script` | `qlik load_script <app_name> [<app_id>]` | Trigger app reload with live log streaming |
| `pub_script` | `qlik pub_script <app_name> [<app_id>]` | Publish shared space app script to its managed space copy |
| `set_items` | `qlik set_items <app_name> [<app_id>]` | Create/update master measures and dimensions from `measures.json` and `dimensions.json` |
| `pub_items` | `qlik pub_items <app_name> [<app_id>]` | Publish shared space app to managed space app (use after updating master items) |
| `flag_items` | `qlik flag_items <app_name> [<app_id>]` | Highlight all charts using non-master measures or dimensions in red |
| `unflag_items` | `qlik unflag_items <app_name> [<app_id>]` | Restore background colors of all flagged charts |
| `set_tenant` | `qlik set_tenant <url>` | Save tenant URL to config file |
| `set_tenant_api_key` | `qlik set_tenant_api_key <key>` | Save API key to config file |
| `get_tenant` | `qlik get_tenant` | Show current tenant URL and API key |
| `help` | `qlik help` | List available commands |

The optional `<app_id>` disambiguates when multiple apps share the same name.

## Typical Workflow

### Script

```
qlik get_app "MyApp"      # 1. Download script tabs as .qvs files
# ... edit .qvs files ... # 2. Make changes locally
qlik set_script "MyApp"   # 3. Validate & push script back to app
qlik load_script "MyApp"  # 4. Reload the app (streams logs)
qlik pub_script "MyApp"   # 5. Publish to managed space
```

### Master Items

```
qlik get_app "MyApp"      # 1. Download master measures + dimensions → masteritems/
# ... edit JSON files ... # 2. Add/modify entries in measures.json / dimensions.json
qlik set_items "MyApp"    # 3. Create/update measures and dimensions in the app
qlik pub_items "MyApp"    # 4. Publish to managed space
```

**set_items behaviour:**
- Matches items by `id` first, falling back to `title` for new items (no id yet).
- After `set_items`, `get_app` is run automatically so the local JSON reflects Qlik's assigned GUIDs.
- Any `id` set manually for a new item will be overwritten by Qlik's own GUID.
- Changing an existing item's `id` causes it to be treated as a brand-new item on the next run.
- Removing an item from the JSON does **not** delete it from the app — `set_items` is additive/update-only. To delete, remove it in Qlik then run `qlik get_app` to sync.
- If the title fallback finds more than one match in the app, the run is aborted with an error listing the conflicting IDs — resolve in `measures.json` / `dimensions.json` and re-run.
- `measures.json` and `dimensions.json` must be named exactly as such — a clear error is raised if either file is missing.

## Local File Structure

Files are stored relative to the current working directory:

```
Apps/
  {appId}/
    {SanitizedAppName}/
      scripts/
        Main.qvs              # First tab (if content before first marker)
        0___TabName1.qvs      # Tabs prefixed with index for ordering
        1___TabName2.qvs
        2___TabName3.qvs
      masteritems/
        measures.json         # Master measures (get_app / set_items)
        dimensions.json       # Master dimensions (get_app / set_items)
      Layout/
        Sheets/
          {SheetName}/
            {objId}.json      # Sheet object definitions (get_app)
```

**measures.json schema:**
```json
[{ "id": "abc123", "title": "Total Sales", "definition": "Sum(Sales)", "label": "='Total Sales'", "description": "", "fmt": "#,##0.00", "tags": [] }]
```

**dimensions.json schema:**
```json
[{ "id": "def456", "title": "Customer", "definition": "CustomerName", "label": "Customer", "label_expression": "='Customer'", "description": "", "tags": [] }]
```

### File Conventions

- **Tab ordering**: Files are prefixed `{index}___` (e.g. `0___`, `1___`) to preserve tab order.
- **Line endings**: Qlik uses `\r` only (not `\r\n`). The CLI normalizes this automatically, but when editing .qvs files directly, preserve `\r` line endings.
- **Tab markers**: Tabs are delimited by `///$tab TabName` in the combined script. The CLI handles splitting/joining automatically.
- **Filename sanitization**: Characters `<>:"/\|?*` are replaced with `_`.

## Editing .qvs Files

When modifying Qlik scripts locally:

1. Run `qlik get_app "AppName"` first to pull the current script.
2. Edit the .qvs files in `Apps/{appId}/{AppName}/scripts/`.
3. Do NOT rename files or change the `{index}___` prefix unless reordering tabs.
4. Do NOT add or remove the `///$tab` markers inside files — the CLI adds them when combining.
5. Run `qlik set_script "AppName"` to validate syntax and push changes.

## Important Notes

- The `load_script` command streams logs in real-time and clears the terminal on each poll. It runs until reload completes or Ctrl+C is pressed.
- The `pub_script` / `pub_items` commands require the app to have been published at least once from the Qlik UI before CLI publishing works.
- The `set_script` command validates script syntax via the API before pushing. Validation results are printed as JSON.
- All commands operate on **shared space** apps. Publishing copies to the corresponding managed space app.
