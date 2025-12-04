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

* Expose the `qlik` command by adding the absolute path for the qlik.cmd your system environment variables.
* Add a new entry under your "Path" environment variable e.g. `C:\Users\<YOU>\AppData\Local\Programs`.  
* This will expose `qlik.cmd` during runtime.

### 4. Set API Key

1. Generate an API key from your Qlik Cloud tenant
2. Set it as an environment variable:
   - Variable name: `_QLIK_API_KEY_`
   - Variable value: Your API key


## Examples
Navigate to a new project directory:
Run in terminal:

```bash
c:\users\projects\mynewproject
```

```bash
c:\users\projects\mynewproject> qlik help
```

