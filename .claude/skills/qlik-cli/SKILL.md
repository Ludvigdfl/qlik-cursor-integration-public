---
name: qlik-cli
description: Custom CLI for managing Qlik Sense Cloud app scripts, reloads, and publishing. Use when the user asks to get, edit, set, reload, or publish Qlik app scripts, or when working with .qvs files in the scripts/ directory. Triggers on references to Qlik apps, Qlik scripts, reload tasks, or the "qlik" command.
---

# Qlik CLI

Custom CLI at `qlik/qlik.cmd` for managing Qlik Sense Cloud apps via the REST API.

## Prerequisites

Tenant URL and API key are stored in `qlik/.qlik_config.json` (gitignored). Configure them once with:

```
qlik set_tenant <tenant_url>
qlik set_tenant_api_key <api_key>
```

Values take effect immediately for all subsequent commands. As a fallback, the CLI also reads `_QLIK_TENANT_URL_` and `_QLIK_API_KEY_` environment variables if the config file is absent.

## Commands

Invoke via Bash: `PYTHONIOENCODING=utf-8 qlik/qlik.cmd <command> <args>`

| Command | Usage | Description |
|---------|-------|-------------|
| `get` | `qlik get <app_name> [<app_id>]` | Download app script, split into .qvs tab files |
| `get_space` | `qlik get_space <space_name>` | Download scripts for all apps in a shared space |
| `set` | `qlik set <app_name> [<app_id>]` | Validate and upload local .qvs files as app script |
| `load` | `qlik load <app_name> [<app_id>]` | Trigger app reload with live log streaming |
| `pub` | `qlik pub <app_name> [<app_id>]` | Publish shared space app to its managed space copy |
| `rem` | `qlik rem <app_name> [<app_id>]` | Delete local script directory for the app |
| `set_tenant` | `qlik set_tenant <url>` | Save tenant URL to config file |
| `set_tenant_api_key` | `qlik set_tenant_api_key <key>` | Save API key to config file |
| `check_tenant` | `qlik check_tenant` | Print current tenant URL and API key |
| `help` | `qlik help` | List available commands |

The optional `<app_id>` disambiguates when multiple apps share the same name.

## Typical Workflow

```
qlik get "MyApp"          # 1. Download script tabs as .qvs files
# ... edit .qvs files ... # 2. Make changes locally
qlik set "MyApp"          # 3. Validate & push script back to app
qlik load "MyApp"         # 4. Reload the app (streams logs)
qlik pub "MyApp"          # 5. Publish to managed space
```

## Local File Structure

Scripts are stored relative to the current working directory:

```
scripts/
  {SanitizedAppName}/
    {appId}/
      Main.qvs              # First tab (if content before first marker)
      0___TabName1.qvs       # Tabs prefixed with index for ordering
      1___TabName2.qvs
      2___TabName3.qvs
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