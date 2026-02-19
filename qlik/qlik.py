import sys
import os
import json
import time
from qlik_script import QlikScript

def get(App_Name:str, App_Id:str = None):
    """Get script from Qlik app, parse tabs, and save to files."""
    Qlik = QlikScript()
    Qlik.empty_script_directory(App_Name, App_Id)

    app_script        = Qlik.get_script(App_Name, App_Id)
    app_script_tabbed = Qlik.parse_script_tabs(app_script)

    Qlik.save_tabs_as_qvs_files(app_script_tabbed, App_Name, App_Id)


def get_space(Space_Name:str):
    """Get script from all apps in shared space."""
    Qlik = QlikScript()

    apps = Qlik.get_apps_in_space(Space_Name)
    for app in apps:
        App_Name = app["name"]
        App_Id = app["resourceId"]
        Qlik.empty_script_directory(App_Name, App_Id)

        app_script        = Qlik.get_script(App_Name, App_Id)
        app_script_tabbed = Qlik.parse_script_tabs(app_script)

        Qlik.save_tabs_as_qvs_files(app_script_tabbed, App_Name, App_Id)


def set(App_Name:str, App_Id:str = None):
    """Set script in Qlik app with validation."""
    Qlik = QlikScript()
    script_tabbed = Qlik.get_app_script_tabbed(App_Name, App_Id)

    print("Script syntax validation:")
    Qlik.validate_script_syntax(script_tabbed)
    Qlik.publish_app_script(script_tabbed, App_Name, App_Id, version_message="test")
    print(f"{App_Name} script set successfully")


def rem(App_Name:str, App_Id:str = None):
    """Empty the script directory."""
    Qlik = QlikScript()
    Qlik.empty_script_directory(App_Name, App_Id)


def pub(App_Name:str, App_Id:str = None):
    """Publish app in Shared Space to Managed Space."""
    Qlik = QlikScript()
    Qlik.publish_app(App_Name, App_Id)


def load(App_Name:str, App_Id:str = None):
    """Reload app and stream reload logs."""
    Qlik = QlikScript()
    reload_id = Qlik.reload_app(App_Name, App_Id)
    
    # Stream logs with terminal clearing to mimic real-time streaming
    print("Streaming reload logs (press Ctrl+C to stop):\n")
    time.sleep(1)  # Brief pause before starting
    
    try:
        for update in Qlik.stream_reload_log(reload_id, poll_interval=1.0, clear_on_update=True):
            # Clear terminal and redraw full log
            Qlik._clear_terminal()
            
            # Print header
            print("=" * 80)
            print(f"Reload ID: {reload_id} | Status: {update['status']}")
            print("=" * 80)
            print()
            
            # Print the full log
            if update['log']:
                print(update['log'])
            
            # Show status indicator
            if update['is_complete']:
                print("\n" + "=" * 80)
                if update['status'] == 'SUCCEEDED':
                    print("✅ Reload completed successfully!")
                elif update['status'] == 'FAILED':
                    print("❌ Reload failed!")
                else:
                    print(f"Reload status: {update['status']}")
                break
    
    except KeyboardInterrupt:
        print("\n\nReload monitoring interrupted by user.")
        print(f"Reload ID: {reload_id}")
        print("You can check the status later using: Qlik.get_reload_log(reload_id)")



def _config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qlik_config.json")


def _read_config() -> dict:
    path = _config_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def _write_config(key: str, value: str):
    config = _read_config()
    config[key] = value
    with open(_config_path(), "w") as f:
        json.dump(config, f, indent=2)


def set_tenant(tenant_url: str):
    """Set the Qlik tenant URL."""
    _write_config("_QLIK_TENANT_URL_", tenant_url)
    print(f"_QLIK_TENANT_URL_ set to: {tenant_url}")


def set_tenant_api_key(api_key: str):
    """Set the Qlik API key."""
    _write_config("_QLIK_API_KEY_", api_key)
    print("_QLIK_API_KEY_ set successfully")


def check_tenant():
    """Print the configured tenant URL and API key."""
    config = _read_config()
    tenant_url = config.get("_QLIK_TENANT_URL_") or os.getenv("_QLIK_TENANT_URL_", "(not set)")
    api_key    = config.get("_QLIK_API_KEY_")    or os.getenv("_QLIK_API_KEY_",    "(not set)")
    print(f"Tenant URL: {tenant_url}")
    print(f"API Key:    {api_key}")


def help():
    print("Available commands:")
    print("🟢 qlik get                <app_name>  [<app_id>]: Get script from the Qlik shared space app")
    print("🟢 qlik get_space          <space_name>:           Get script from all apps in shared space")
    print("🟢 qlik set                <app_name>  [<app_id>]: Set script for the Qlik shared space app")
    print("🟢 qlik load               <app_name>  [<app_id>]: Reload the Qlik shared space app")
    print("🟢 qlik pub                <app_name>  [<app_id>]: Publish the Qlik shared space app to the Qlik managed space app")
    print("🟢 qlik rem                <app_name>  [<app_id>]: Empty the local script directory for app")
    print("🟢 qlik set_tenant         <tenant_url>:           Set the Qlik tenant URL (persists across terminals)")
    print("🟢 qlik set_tenant_api_key <api_key>:              Set the Qlik API key (persists across terminals)")
    print("🟢 qlik check_tenant:                              Print the configured tenant URL and API key")


commands = {
    "get": get,
    "get_space": get_space,
    "set": set,
    "rem": rem,
    "load": load,
    "pub": pub,
    "set_tenant": set_tenant,
    "set_tenant_api_key": set_tenant_api_key,
    "check_tenant": check_tenant,
    "help": help,
}

try:
    tool_to_run = sys.argv[1]     

    if tool_to_run not in commands.keys():
        raise ValueError(f"Unknown tool: {tool_to_run}. Available: {', '.join(commands.keys())}")
except IndexError:
    print("Please provide a function to run.")
    print(f"Available functions: {', '.join(commands.keys())}")
    sys.exit(1)
except ValueError as e:
    print(e)
    sys.exit(1)



try:
    if tool_to_run == "get":
        if len(sys.argv) == 4:
            get(sys.argv[2], sys.argv[3])
        else:
            get(sys.argv[2])

    elif tool_to_run == "get_space":
        get_space(sys.argv[2])

    elif tool_to_run == "set":
        if len(sys.argv) == 4:
            set(sys.argv[2], sys.argv[3])
        else:
            set(sys.argv[2])

    elif tool_to_run == "load":
        if len(sys.argv) == 4:
            load(sys.argv[2], sys.argv[3])
        else:
            load(sys.argv[2])

    elif tool_to_run == "pub":
        if len(sys.argv) == 4:
            pub(sys.argv[2], sys.argv[3])
        else:
            pub(sys.argv[2])

    elif tool_to_run == "rem":
        if len(sys.argv) == 4:
            rem(sys.argv[2], sys.argv[3])
        else:
            rem(sys.argv[2])
        
    elif tool_to_run == "set_tenant":
        set_tenant(sys.argv[2])

    elif tool_to_run == "set_tenant_api_key":
        set_tenant_api_key(sys.argv[2])

    elif tool_to_run == "check_tenant":
        check_tenant()

    elif tool_to_run == "help":
        help()

except Exception as e:
    print(str(e))
    sys.exit(1)

 