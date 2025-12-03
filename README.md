# Basic CLI for Qlik Cloud

## Setup

### 1. Install Syntax Highlighting

1. Open Cursor
2. Go to **Extensions** (or press `Ctrl+Shift+X`)
3. Click the **...** menu → **Install from VSIX...**
4. Select: `static/qlik highlight/gimly81.qlik-0.5.0.vsix`
5. Restart Cursor

### 2. Install Filename Highlighting

**Optional:** Install VSCode Icons Theme (`vscode-icons-team.vscode-icons`) and activate it to display Qlik Sense icons for `.qvs` files.

### 3. Add to Environment Variables

Expose the `qlik` command by adding folder for .cmd to the system environment variables:
Add a new entry under your "Path" environment variable: `/static/qlik/`  
This will make the script look for any .cmd in that folder (qlik.cmd)
The qlik.cmd then handles the rest executing scripts in 
- static/qlik/qlik_script.py and 
- static/qlik/qlik.py and 

### 4. Set API Key

1. Generate an API key from your Qlik Cloud tenant
2. Set it as an environment variable:
   - Variable name: `_QLIK_API_KEY_`
   - Variable value: Your API key

### 5. Get Started

Run in terminal:
```bash
qlik help
```
