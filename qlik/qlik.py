import sys
import time
from qlik_script import QlikScript 

def get(App_Name:str):
    """Get script from Qlik app, parse tabs, and save to files."""
    Qlik = QlikScript()
    Qlik.empty_script_directory(App_Name)

    app_script        = Qlik.get_script(App_Name)
    app_script_tabbed = Qlik.parse_script_tabs(app_script)

    Qlik.save_tabs_as_qvs_files(app_script_tabbed, App_Name)


def set(App_Name:str):
    """Set script in Qlik app with validation."""
    Qlik = QlikScript()
    script_tabbed = Qlik.get_app_script_tabbed(App_Name)

    print("Script syntax validation:")
    Qlik.validate_script_syntax(script_tabbed)
    Qlik.publish_app_script(script_tabbed, App_Name, "test")
    print(f"{App_Name} script set successfully")


def rem(App_Name:str):
    """Empty the script directory."""
    Qlik = QlikScript()
    Qlik.empty_script_directory(App_Name)


def pub(App_Name:str = None):
    """Publish app in Shared Space to Managed Space."""
    Qlik = QlikScript()
    Qlik.publish_app(App_Name)


def load(App_Name:str):
    """Reload app and stream reload logs."""
    Qlik = QlikScript()
    reload_id = Qlik.reload_app(App_Name)
    
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



def help():
    print("Available commands:")
    print("🟢 qlik get <app_name>:  Get script from the Qlik shared space app")
    print("🟢 qlik set <app_name>:  Set script for the Qlik shared space app")
    print("🟢 qlik load <app_name>: Reload the Qlik shared space app")
    print("🟢 qlik pub <app_name>:  Publish the Qlik shared space app to the Qlik managed space app")
    print("🟢 qlik rem <app_name>:  Empty the local script directory for app")


commands = {
    "get": get,
    "set": set,
    "rem": rem,
    "load": load,
    "pub": pub,
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

if tool_to_run == "get":
    get(sys.argv[2]) 
elif tool_to_run == "set":
    set(sys.argv[2])
elif tool_to_run == "load":
    load(sys.argv[2])
elif tool_to_run == "rem":
    rem(sys.argv[2])
elif tool_to_run == "pub":
    pub(sys.argv[2])
elif tool_to_run == "help":
    help()

 