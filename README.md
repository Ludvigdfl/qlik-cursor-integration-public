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

### 4. Set API Key

1. Generate an API key from your Qlik Cloud tenant
2. Set it as an environment variable:
   - Variable name: `_QLIK_API_KEY_`
   - Variable value: Your API key

### 5. Set Cloud URL
   - Variable name: `_QLIK_TENANT_URL_`
   - Variable value: https://your_domain.qlikcloud.com/api/v1
1. 

## Examples
⚠️ Important - Run the commands below in a separate folder - i.e. not within the root of cli files (`C:\Users\<YOU>\AppData\Local\Programs`).
- Navigate to a new project directory:
- Run in terminal:

```bash
c:\users\projects\mynewproject
```

```bash
c:\users\projects\mynewproject> qlik help
```

