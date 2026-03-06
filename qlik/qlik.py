import sys
import os
import json
import time
import inspect
from pathlib import Path
from qlik_script import QlikScript
from qlik_masteritems import Qlik_Masteritems


def _config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qlik_config.json")


def _read_config() -> dict:
    path = _config_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def _write_config(key: str, value: str):
    path = _config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    config = _read_config()
    config[key] = value
    with open(path, "w") as f:
        json.dump(config, f, indent=2)

def _masteritems_dir(App_Name: str, App_Id: str = None) -> tuple:
    """Resolve app info and return the masteritems save_dir path."""
    Qlik = QlikScript()
    app_info = Qlik.get_app_by_name(App_Name, App_Id)
    save_dir = QlikScript._get_project_root() / "Apps" / app_info["appId"] / app_info["sanitizedAppName"] / "masteritems"
    return app_info["appId"], save_dir



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

def get_items(App_Name: str, App_Id: str = None):
    """Get master measures and dimensions from Qlik app and save to masteritems/measures.json and dimensions.json."""
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    measures = Qlik.get_measures()
    dimensions = Qlik.get_dimensions()
    save_dir.mkdir(parents=True, exist_ok=True)
    with open(save_dir / "measures.json", "w", encoding="utf-8") as f:
        json.dump(measures, f, indent=4)
    with open(save_dir / "dimensions.json", "w", encoding="utf-8") as f:
        json.dump(dimensions, f, indent=4)
    print("✅ Measures and dimensions fetched successfully!")
    Qlik.close()


def set_items(App_Name: str, App_Id: str = None):
    """Set master measures and dimensions in Qlik app from masteritems/measures.json and dimensions.json (changed items only)."""
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    changed_measures, changed_dimensions = Qlik.get_items_changed()
    Qlik.create_measures(changed_measures)
    Qlik.create_dimensions(changed_dimensions)
    Qlik.close()


def pub_items(App_Name: str, App_Id: str = None):
    """Publish shared space app to managed space app (e.g. after updating master items)."""
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    Qlik.publish_app()
    Qlik.close()


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


def set_tenant(tenant_url: str):
    """Set the Qlik tenant URL."""
    _write_config("_QLIK_TENANT_URL_", tenant_url)
    print(f"_QLIK_TENANT_URL_ set to: {tenant_url}")


def set_tenant_api_key(api_key: str):
    """Set the Qlik API key."""
    _write_config("_QLIK_API_KEY_", api_key)
    print("_QLIK_API_KEY_ set successfully")


def get_tenant():
    """Get the current tenant URL and API key."""
    config = _read_config()
    tenant_url = config.get("_QLIK_TENANT_URL_") or os.getenv("_QLIK_TENANT_URL_", "(not set)")
    api_key    = config.get("_QLIK_API_KEY_")    or os.getenv("_QLIK_API_KEY_",    "(not set)")
    print(f"Tenant URL: {tenant_url}")
    print(f"API Key:    {api_key}")


def help():
    print("Available commands:")
    print("🟢 qlik get                  <app_name>  [<app_id>]: Get script from the Qlik shared space app, optionally provide the app_id if multiple apps share the same name")
    print("🟢 qlik get_space            <space_name>:           Get script from all apps in shared space")
    print("🟢 qlik set                  <app_name>  [<app_id>]: Set script for the Qlik shared space app, optionally provide the app_id if multiple apps share the same name")
    print("🟢 qlik load                 <app_name>  [<app_id>]: Reload the Qlik shared space app, optionally provide the app_id if multiple apps share the same name")
    print("🟢 qlik pub                  <app_name>  [<app_id>]: Publish the Qlik shared space app to the Qlik managed space app, optionally provide the app_id if multiple apps share the same name")
    print("🟢 qlik rem                  <app_name>  [<app_id>]: Empty the local script directory for app")
    print("")
    print("🟢 qlik get_items            <app_name>  [<app_id>]: Get all master measures and dimensions from app and save to measures.json and dimensions.json")
    print("🟢 qlik set_items            <app_name>  [<app_id>]: Set all master measures and dimensions in app from measures.json and dimensions.json")
    print("🟢 qlik pub_items            <app_name>  [<app_id>]: Publish shared space app to managed space app (use after updating master items)")
    print("")
    print("🟢 qlik set_tenant           <tenant_url>:           Set the Qlik tenant URL. e.g. https://{tenant}.{region}.qlikcloud.com")
    print("🟢 qlik set_tenant_api_key   <api_key>:              Set the Qlik API key")
    print("🟢 qlik get_tenant:                                  Get the current tenant URL and API key")


commands = {
    "get": get,
    "get_space": get_space,
    "set": set,
    "rem": rem,
    "load": load,
    "pub": pub,
    "get_items": get_items,
    "set_items": set_items,
    "pub_items": pub_items,
    "set_tenant": set_tenant,
    "set_tenant_api_key": set_tenant_api_key,
    "get_tenant": get_tenant,
    "help": help,
}

try:
    tool_to_run = sys.argv[1]     

    if tool_to_run not in commands.keys():
        raise ValueError(f"Unknown tool: {tool_to_run}. Available: {', '.join(commands.keys())}")
except IndexError:
    help()
    sys.exit(1)
except ValueError as e:
    print(e)
    sys.exit(1)



def _validate_and_call(cmd_name, func, args):
    params = list(inspect.signature(func).parameters.values())
    min_args = sum(1 for p in params if p.default is inspect.Parameter.empty)
    max_args = len(params)
    n_args = len(args)

    if n_args < min_args or n_args > max_args:
        parts = [f"qlik {cmd_name}"]
        for p in params:
            parts.append(f"[<{p.name}>]" if p.default is not inspect.Parameter.empty else f"<{p.name}>")
        usage = " ".join(parts)
        expected = f"{min_args}-{max_args}" if min_args != max_args else (f"exactly {min_args}" if min_args else "no")
        print(f"Error: '{cmd_name}' takes {expected} argument(s), got {n_args}.")
        print(f"Usage: {usage}")
        sys.exit(1)

    func(*args)


try:
    _validate_and_call(tool_to_run, commands[tool_to_run], sys.argv[2:])

except SystemExit:
    raise
except Exception as e:
    print(str(e))
    sys.exit(1)

 