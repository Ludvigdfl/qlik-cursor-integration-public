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
    save_dir = QlikScript._get_project_root() / app_info["sanitizedSpaceName"] / app_info["sanitizedAppName"] / app_info["appId"] / "MasterItems"
    return app_info["appId"], save_dir



def get(App_Name: str, App_Id: str = None):
    """Get script from Qlik app, parse tabs, and save to files."""
    print(f"... Fetching ...")
    Qlik = QlikScript()
    Qlik.empty_script_directory(App_Name, App_Id)
    app_script        = Qlik.get_script(App_Name, App_Id)
    app_script_tabbed = Qlik.parse_script_tabs(app_script)
    Qlik.save_tabs_as_qvs_files(app_script_tabbed, App_Name, App_Id)


def get_app(App_Name: str, App_Id: str = None):
    """Get script, master items, and sheet objects from Qlik app."""
    get(App_Name, App_Id)
    get_items(App_Name, App_Id, silent=True)
    get_objects(App_Name, App_Id)


def get_space(Space_Name: str):
    """Get script, master items, and sheet objects for all apps in a shared space."""
    Qlik = QlikScript()
    apps = Qlik.get_apps_in_space(Space_Name)
    print(f"... Fetching {len(apps)} app(s) ...")
    for app in apps:
        get_app(app["name"], app["resourceId"])
        print()
    print(f"Space {Space_Name} fetched successfully")


def set_script(App_Name:str, App_Id:str = None):
    """Set script in Qlik app with validation."""
    Qlik = QlikScript()
    script_tabbed = Qlik.get_app_script_tabbed(App_Name, App_Id)

    print("Script syntax validation:")
    Qlik.validate_script_syntax(script_tabbed)
    Qlik.publish_app_script(script_tabbed, App_Name, App_Id, version_message="test")
    print(f"{App_Name} script set successfully")



def pub_script(App_Name:str, App_Id:str = None):
    """Publish app in Shared Space to Managed Space."""
    Qlik = QlikScript()
    Qlik.publish_app(App_Name, App_Id)

def get_items(App_Name: str, App_Id: str = None, silent: bool = False):
    """Get master measures and dimensions from Qlik app and save to masteritems/measures.json and dimensions.json."""
    if not silent:
        print(f"... Fetching ...")
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    measures = Qlik.get_measures()
    dimensions = Qlik.get_dimensions()
    save_dir.mkdir(parents=True, exist_ok=True)
    with open(save_dir / "measures.json", "w", encoding="utf-8") as f:
        json.dump(measures, f, indent=4)
    with open(save_dir / "dimensions.json", "w", encoding="utf-8") as f:
        json.dump(dimensions, f, indent=4)
    Qlik.close()
    print(f"✅ {App_Name} - items")


def set_items(App_Name: str, App_Id: str = None):
    """Set master measures and dimensions in Qlik app from masteritems/measures.json and dimensions.json (changed items only)."""
    
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    changed_measures, changed_dimensions = Qlik.get_items_changed()
    
    # Create measures and dimensions in Qlik
    Qlik.create_measures(changed_measures)
    Qlik.create_dimensions(changed_dimensions)
    
    # Get measures and dimensions from Qlik to sync IDs with local files (Qlik generates GUID even though we provide an ID or not)
    measures = Qlik.get_measures()
    dimensions = Qlik.get_dimensions()
    with open(save_dir / "measures.json", "w", encoding="utf-8") as f:
        json.dump(measures, f, indent=4)
    with open(save_dir / "dimensions.json", "w", encoding="utf-8") as f:
        json.dump(dimensions, f, indent=4)
    Qlik.close()


def pub_items(App_Name: str, App_Id: str = None):
    """Publish shared space app to managed space app (e.g. after updating master items)."""
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    Qlik.publish_app()
    Qlik.close()


def flag_items(App_Name: str, App_Id: str = None):
    """Highlight all chart objects with inline (non-master) measures or dimensions by setting a background color.
    Originals are saved to items_diff/diff.json so unflag_items can restore them."""
    color = "#ff6666"
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    Qlik.set_object_background(color)
    Qlik.close()


def unflag_items(App_Name: str, App_Id: str = None):
    """Restore the original background colors of objects highlighted by flag_items."""
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    Qlik.revert_object_background()
    Qlik.close()


def get_objects(App_Name: str, App_Id: str = None):
    """Fetch all sheet objects for an app and save each as a JSON file under Layout/Sheets/<sheet>/<obj_id>.json."""
    app_id, save_dir = _masteritems_dir(App_Name, App_Id)
    objects_root = save_dir.parent / "Layout" / "Sheets"
    Qlik = Qlik_Masteritems(app_id=app_id, save_dir=save_dir)
    total = Qlik.get_objects(objects_root)
    Qlik.close()
    print(f"✅ {App_Name} - objects")


def load_script(App_Name:str, App_Id:str = None):
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
    print("-----------------------------------------------------------------------------------------------------------------------------")
    print("   Command                   <arg1>         [<arg2>]      Description")
    print("-----------------------------------------------------------------------------------------------------------------------------")
    print("🟢 qlik set_tenant           <tenant_url>                Set <tenant_url> - https://{tenant}.{region}.qlikcloud.com")
    print("🟢 qlik set_tenant_api_key   <api_key>                   Set <api_key>")
    print("🟢 qlik get_tenant                                       Check active tenant URL and API key")
    print("")
    print("🟢 qlik get_space            <space_name>                Get script, master items, and sheet objects for all apps in a shared <space_name>")
    print("🟢 qlik get_app              <app_name>     [<app_id>]   Get script, master items, and sheet objects from shared space <app>")
    print("")
    print("🟢 qlik set_script           <app_name>     [<app_id>]   Set script for shared space <app> ")
    print("🟢 qlik load_script          <app_name>     [<app_id>]   Reload a shared space <app>")
    print("🟢 qlik pub_script           <app_name>     [<app_id>]   Publish a shared space <app> to a managed space app")
    print("")
    print("🟢 qlik set_items            <app_name>     [<app_id>]   Set all master measures and dimensions in shared space <app>")
    print("🟢 qlik pub_items            <app_name>     [<app_id>]   Publish shared space <app> to managed space app")
    print("")
    print("🟢 qlik flag_items           <app_name>     [<app_id>]   Highlight all charts using hard coded measures or dimensions in red.")
    print("🟢 qlik unflag_items         <app_name>     [<app_id>]   Restore background colors of all charts.")
    print("")
commands = {
    "get_app": get_app,
    "get_space": get_space,
    "set_script": set_script,
    "load_script": load_script,
    "pub_script": pub_script,
    "set_items": set_items,
    "pub_items": pub_items,
    "flag_items": flag_items,
    "unflag_items": unflag_items,
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

 