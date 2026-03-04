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
| `get` | `qlik get <app_name> [<app_id>]` | Download app script, split into .qvs tab files |
| `get_space` | `qlik get_space <space_name>` | Download scripts for all apps in a shared space |
| `set` | `qlik set <app_name> [<app_id>]` | Validate and upload local .qvs files as app script |
| `load` | `qlik load <app_name> [<app_id>]` | Trigger app reload with live log streaming |
| `pub` | `qlik pub <app_name> [<app_id>]` | Publish shared space app to its managed space copy |
| `rem` | `qlik rem <app_name> [<app_id>]` | Delete local script directory for the app |
| `get_ms` | `qlik get_ms <app_name> [<app_id>]` | Download all master measures → `masteritems/measures.json` |
| `set_ms` | `qlik set_ms <app_name> [<app_id>]` | Create/update master measures from `measures.json` |
| `get_dim` | `qlik get_dim <app_name> [<app_id>]` | Download all master dimensions → `masteritems/dimensions.json` |
| `set_dim` | `qlik set_dim <app_name> [<app_id>]` | Create/update master dimensions from `dimensions.json` |
| `set_tenant` | `qlik set_tenant <url>` | Save tenant URL to config file |
| `set_tenant_api_key` | `qlik set_tenant_api_key <key>` | Save API key to config file |
| `get_tenant` | `qlik get_tenant` | Get current tenant URL and API key |
| `help` | `qlik help` | List available commands |

The optional `<app_id>` disambiguates when multiple apps share the same name.

## Typical Workflow

### Script

```
qlik get "MyApp"          # 1. Download script tabs as .qvs files
# ... edit .qvs files ... # 2. Make changes locally
qlik set "MyApp"          # 3. Validate & push script back to app
qlik load "MyApp"         # 4. Reload the app (streams logs)
qlik pub "MyApp"          # 5. Publish to managed space
```

### Master Items

```
qlik get_ms "MyApp"       # 1. Download master measures → masteritems/measures.json
qlik get_dim "MyApp"      # 1. Download master dimensions → masteritems/dimensions.json
# ... edit JSON files ... # 2. Add/modify entries locally
qlik set_ms "MyApp"       # 3. Create/update measures in the app
qlik set_dim "MyApp"      # 3. Create/update dimensions in the app
```

`set_ms` / `set_dim` match items by `id` first, then by `title`. If more than one item in the app shares the same title, the item is skipped and written to `measures_duplicates.json` / `dimensions_duplicates.json` for manual review.

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
        measures.json         # Master measures (get_ms / set_ms)
        dimensions.json       # Master dimensions (get_dim / set_dim)
        measures_duplicates.json    # Written when duplicate measures are found
        dimensions_duplicates.json  # Written when duplicate dimensions are found
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

1. Run `qlik get "AppName"` first to pull the current script.
2. Edit the .qvs files in `scripts/{AppName}/{appId}/`.
3. Do NOT rename files or change the `{index}___` prefix unless reordering tabs.
4. Do NOT add or remove the `///$tab` markers inside files - the CLI adds them when combining.
5. Run `qlik set "AppName"` to validate syntax and push changes.

## Important Notes

- The `load` command streams logs in real-time and clears the terminal on each poll. It runs until reload completes or Ctrl+C is pressed.
- The `pub` command requires the app to have been published at least once from the Qlik UI before CLI publishing works.
- The `set` command validates script syntax via the API before publishing. Validation results are printed as JSON.
- All commands operate on **shared space** apps. Publishing copies to the corresponding managed space app.