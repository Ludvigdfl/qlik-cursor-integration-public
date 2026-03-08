import requests
import time
import json
import re
import os
import sys
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Iterator


class QlikScript:
    @staticmethod
    def _load_config() -> dict:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qlik_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        return {}

    def __init__(self):
        config = self._load_config()
        tenant_url = config.get("_QLIK_TENANT_URL_")
        self.api_key = config.get("_QLIK_API_KEY_")

        if not tenant_url:
            print("ERROR: _QLIK_TENANT_URL_ is not set. Run: qlik set_tenant <url>")
            sys.exit(1)
        if not self.api_key:
            print("ERROR: _QLIK_API_KEY_ is not set. Run: qlik set_tenant_api_key <key>")
            sys.exit(1)

        tenant_url = tenant_url.rstrip("/")
        if tenant_url.endswith("/api/v1"):
            tenant_url = tenant_url[:-len("/api/v1")]
        self.base_url = tenant_url + "/api/v1"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
       
    
 
    def _get_all_paginated(self, url: str) -> List[Dict]:
        """Fetch all pages of data from a paginated Qlik API endpoint.

        Follows links.next.href until all pages are retrieved.
        """
        all_data = []
        while url:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            body = response.json()
            all_data.extend(body.get("data", []))
            url = body.get("links", {}).get("next", {}).get("href", None)
        return all_data

    def get_app_by_name(self, app_name: str, app_id: str = None) -> Dict:
        """Get app info (appName) by app_name."""
        
        url = f"{self.base_url}/items?resourceType=app&spaceType=shared&name={app_name}"

        if app_id:
            url = f"{self.base_url}/items?resourceType=app&spaceType=shared&name={app_name}&resourceId={app_id}"

        response_data = self._get_all_paginated(url)

        if not response_data:
            raise ValueError(f"No app found with name {app_name}")
        
        multiple_apps = ''
        for app in response_data:
            multiple_apps += f"\n{app['name']} ({app['resourceId']})"

        # Qlik performs a search.
        # Searching for "Finans" will return both "Finans" and "Finans2"
        if app_id:
            response_data = [app for app in response_data if app["resourceId"] == app_id]
        else:
            response_data = [app for app in response_data if app["name"] == app_name]
    
        if len(response_data) > 1:
            raise ValueError(f"""Multiple apps found similar or equal to ´{app_name}´. 
            Please provide more specific app_name or bothapp_name & app_id to disambiguate.
            Available apps: 
            {multiple_apps}
            """)
        
        app = response_data[0]
     
        app_dict = {
            "sanitizedAppName": re.sub(r'[<>:"/\\|?*]', '_', app.get("name", "")),
            "appName": app.get("name"),
            "appId": app.get("resourceId"),
            "appItemId": app.get("id"),
            "spaceId": app.get("spaceId"),
        }

        if "spaceId" in app_dict and len(app_dict["spaceId"]) > 0:
            space_info = self.get_space_type(app_dict["spaceId"])
            app_dict["spaceType"] = space_info["type"]
            app_dict["spaceName"] = space_info["name"]
            app_dict["sanitizedSpaceName"] = re.sub(r'[<>:"/\\|?*]', '_', space_info["name"])
        
        return app_dict
    
    @staticmethod
    def _get_project_root() -> Path:
        """Get the project root directory (where the scripts folder is located)."""    
        return Path.cwd()

    def empty_script_directory(self, app_name: str, app_id: str = None):
        app_info = self.get_app_by_name(app_name, app_id)
        project_root = self._get_project_root()
        script_dir = project_root / app_info["sanitizedSpaceName"] / app_info["sanitizedAppName"] / app_info["appId"] / "Script"

        if script_dir.exists():
            shutil.rmtree(script_dir)

    def get_app_info(self, app_name: str, app_id: str = None) -> Dict:
        app_info = self.get_app_by_name(app_name, app_id)
        url = f"{self.base_url}/apps/{app_info['appId']}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    

    def get_script(self, app_name: str, app_id: str = None) -> Dict:
        app_info = self.get_app_by_name(app_name, app_id)
        self.empty_script_directory(app_name, app_id)
        url = f"{self.base_url}/apps/{app_info['appId']}/scripts"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        scripts_list = data.get("scripts", [])
        if not scripts_list:
            raise ValueError(f"No scripts found in stored file for app {app_info['appId']}")
        
        script_id = scripts_list[0].get("scriptId")
        if not script_id:
            raise ValueError(f"No scriptId found in the first script entry")
        
        url = f"{self.base_url}/apps/{app_info['appId']}/scripts/{script_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()["script"]
         
  
    def parse_script_tabs(self, script: str) -> Dict[str, str]:
        """
        Parse a Qlik script and split it by tab markers (///$tab _TAB_).
        
        Args:
            script: The full Qlik script string
            
        Returns:
            Dictionary mapping i___tab_name to their script content
        """
        # Pattern to match tab markers: ///$tab TABNAME (captures everything until newline)
        tab_pattern = r'///\$tab\s+([^\r\n]+)'
        
        # Find all tab markers and their positions
        matches = list(re.finditer(tab_pattern, script))
        
        if not matches:
            # No tabs found, return as single "Main" tab
            return {"Main": script.strip()}
        
        tabs = {}
        global_index = 0

        # Extract content before the first marker (if any)
        first_tab_content = script[:matches[0].start()].strip()
        if first_tab_content:
            tabs[f"{global_index}___Main"] = first_tab_content
            global_index += 1

        # Extract each named tab
        for i, match in enumerate(matches):
            tab_name = match.group(1).strip()
            key = f"{global_index}___{tab_name}"
            start_pos = match.end()

            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(script)

            tabs[key] = script[start_pos:end_pos].strip()
            global_index += 1

        return tabs


    def save_tabs_as_qvs_files(self, tabs: Dict[str, str], app_name: str, app_id: str = None) -> List[str]:
        """
        Save each tab to a separate .qvs file.
        
        Args:
            tabs: Dictionary mapping tab names to script content
            app_name: Name of the app
            app_id: Optional app ID to resolve ambiguous names
            
        Returns:
            List of file paths created
        """
        app_info = self.get_app_by_name(app_name, app_id)
        project_root = self._get_project_root()
        output_dir = project_root / app_info["sanitizedSpaceName"] / app_info["sanitizedAppName"] / app_info["appId"] / "Script"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        for tab_name, content in tabs.items():
            # Sanitize filename (remove invalid characters)
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', tab_name)
            file_path = output_dir / f"{safe_name}.qvs"
            
            # Normalize line endings to \r only (convert \r\n to \r, and \n to \r)
            normalized_content = content.replace('\r\n', '\r').replace('\n', '\r')
            
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(normalized_content)
            
            created_files.append(str(file_path))
        print(f"✅ {app_name} - script")
        return created_files


    def combine_tabs_from_files(self, app_name: str, app_id: str = None, tab_order: List[str] = None) -> str:
        """
        Combine multiple .qvs files back into a single Qlik script with tab markers.
        
        Args:
            app_name: Name of the app
            app_id: Optional app ID to resolve ambiguous names
            tab_order: Optional list specifying the order of tabs. 
                    If None, files are sorted alphabetically.
                    
        Returns:
            Combined script string with tab markers
        """
        app_info = self.get_app_by_name(app_name, app_id)
        project_root = self._get_project_root()
        scripts_path = project_root / app_info["sanitizedSpaceName"] / app_info["sanitizedAppName"] / app_info["appId"] / "Script"

        if not scripts_path.exists():
            raise ValueError(f"Directory {scripts_path} does not exist")

        # Get all .qvs files
        qvs_files = list(scripts_path.glob("*.qvs"))
        
        if not qvs_files:
            raise ValueError(f"No .qvs files found in {scripts_path}")
        
        # Determine order
        if tab_order:
            # Sort files according to tab_order
            file_dict = {f.stem: f for f in qvs_files}
            ordered_files = []
            for tab_name in tab_order:
                if tab_name in file_dict:
                    ordered_files.append(file_dict[tab_name])
            # Add any remaining files not in tab_order
            for f in qvs_files:
                if f not in ordered_files:
                    ordered_files.append(f)
        else:
            # Sort descending based on first 3 characters of filename (i___tab_name)
            ordered_files = sorted(qvs_files, key=lambda x: x.stem[:3] if len(x.stem) >= 3 else x.stem, reverse=True)
        
        combined_script = []
        
        for qvs_file in ordered_files:
            tab_name = qvs_file.stem
            
            with open(qvs_file, 'r', encoding='utf-8', newline='') as f:
                content = f.read().strip()
            
            if not content:
                continue
            
            # Normalize line endings to \r only
            content = content.replace('\r\n', '\r').replace('\n', '\r')
            
            # Add tab marker (except for Main which comes first)
            if tab_name == "Main" and ordered_files.index(qvs_file) == 0:
                # Main tab at the beginning doesn't need a marker
                combined_script.append(content)
            else:
                combined_script.append(f"///$tab {tab_name}\r{content}")
        
        return "\r\r".join(combined_script)
    

    def get_app_script_tabbed(self, app_name: str, app_id: str = None) -> str:
        app_info = self.get_app_by_name(app_name, app_id)
        project_root = self._get_project_root()
        script_dir = project_root / app_info["sanitizedSpaceName"] / app_info["sanitizedAppName"] / app_info["appId"] / "Script"

        if not script_dir.exists():
            raise ValueError(f"Directory {script_dir} does not exist")

        qvs_files = list(script_dir.glob("*.qvs"))
        if not qvs_files:
            raise ValueError(f"No .qvs files found in {script_dir}")
        
        def _tab_index(stem: str) -> int:
            if '___' in stem:
                try:
                    return int(stem.split('___')[0])
                except ValueError:
                    pass
            return -1  # 'Main' and unrecognised files sort first

        ordered_files = sorted(qvs_files, key=lambda x: _tab_index(x.stem))
        
        combined_parts = []
        for qvs_file in ordered_files:
            tab_name = qvs_file.stem
            with open(qvs_file, 'rb') as f:
                raw_content = f.read()
            
            content = raw_content.decode('utf-8')
            if content:
                content = content.rstrip()
            
            if not content:
                continue
            
            content = content.replace('\r\n', '\r').replace('\n', '\r')
         
            combined_parts.append(f"///$tab {tab_name.split('___')[1]}\r{content}")
        
        combined_script = "\r\r".join(combined_parts)
        return combined_script


    def publish_app_script(self, app_script_string: str, app_name: str, app_id: str = None, version_message: str = "test") -> Dict:
        app_info = self.get_app_by_name(app_name, app_id)
        payload = {
            "script": app_script_string,
            "versionMessage": version_message
        }
  
        url = f"{self.base_url}/apps/{app_info['appId']}/scripts"
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response


    def reload_app(self, app_name: str, app_id: str = None, weight: int = 1, partial: bool = False) -> str:
        app_info = self.get_app_by_name(app_name, app_id)
        url = f"{self.base_url}/reloads"
        payload = {
            "appId": app_info["appId"],
            "weight": weight,
            "partial": partial
        }
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        reload_data = response.json()
        reload_id = reload_data.get("id")
        print("____________")
        print("RELOADING APP")
        return reload_id

    def get_reload_log(self, reload_id: str) -> Dict:
        url = f"{self.base_url}/reloads/{reload_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    

    @staticmethod
    def _clear_terminal():
        """Clear the terminal screen (cross-platform)."""
        if platform.system() == "Windows":
            os.system('cls')
        else:
            os.system('clear')
    

    def stream_reload_log(self, reload_id: str, poll_interval: float = 1.0, 
                         clear_on_update: bool = False) -> Iterator[Dict]:
        """
        Stream reload logs in real-time by polling the reload status.
        
        Args:
            reload_id: The ID of the reload to monitor
            poll_interval: Time in seconds between polls (default: 1.0)
            clear_on_update: If True, clears terminal before each update to mimic streaming
            
        Yields:
            Dictionary with keys:
                - 'log': Full log content (or new content if not clearing)
                - 'status': Current reload status
                - 'is_new': Boolean indicating if this is new content
                - 'is_complete': Boolean indicating if reload is finished
        """
        last_log_length = 0
        
        while True:
            try:
                log_data = self.get_reload_log(reload_id)
                current_status = log_data.get("status", "").upper()
                log_content = log_data.get("log", "")
                
                is_new = len(log_content) > last_log_length
                
                if clear_on_update:
                    yield_data = {
                        'log': log_content,
                        'status': current_status,
                        'is_new': is_new,
                        'is_complete': current_status in ["SUCCEEDED", "FAILED", "CANCELLED"]
                    }
                else:
                    if is_new:
                        new_log = log_content[last_log_length:]
                        yield_data = {
                            'log': new_log,
                            'status': current_status,
                            'is_new': True,
                            'is_complete': current_status in ["SUCCEEDED", "FAILED", "CANCELLED"]
                        }
                    else:
                        yield_data = {
                            'log': '',
                            'status': current_status,
                            'is_new': False,
                            'is_complete': current_status in ["SUCCEEDED", "FAILED", "CANCELLED"]
                        }
                
                yield yield_data
                
                if is_new:
                    last_log_length = len(log_content)
                
                if yield_data['is_complete']:
                    break
                
                time.sleep(poll_interval)
                
            except Exception as e:
                yield {
                    'log': f"Error polling reload status: {str(e)}\n",
                    'status': 'ERROR',
                    'is_new': True,
                    'is_complete': True
                }
                break


    def validate_script_syntax(self, script: str) -> bool:
        url = f"{self.base_url}/apps/validatescript"
        response = requests.post(url, headers=self.headers, json={"script": script})
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))
        return response
    

    def get_app_published_id(self, app_name: str, app_id: str = None) -> str:
        app_info = self.get_app_by_name(app_name, app_id)
        # Get unique ItemID for the app (AppID and ItemID are not the same)
        url = f"{self.base_url}/items?resourceId={app_info['appId']}&resourceType=app"
        items_data = self._get_all_paginated(url)
        app_item_id = items_data[0]["id"]

        # Get unique AppID for the published version of the app
        url = f"{self.base_url}/items/{app_item_id}/publisheditems"
        response_data = self._get_all_paginated(url)
        
        if not response_data or "resourceId" not in response_data[0]:
            raise ValueError("Published app not found or invalid response structure. If app has never been published, publish it once from the UI first.")
        
        return response_data[0]["resourceId"]
         

    def publish_app(self, app_name: str, app_id: str = None):
        app_info = self.get_app_by_name(app_name, app_id)
        app_published_id = self.get_app_published_id(app_name, app_id)

        url = f"{self.base_url}/apps/{app_info['appId']}/publish"
        payload = {"targetId": app_published_id}
        response = requests.put(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        response_json = response.json()
        attributes = response_json.get("attributes", {})
        
        if response.status_code != 200:
            raise ValueError(f"Failed to publish app: {response.status_code} {response.text}")
        else:
            print(f"✅ ´{attributes.get('name')}´ published successfully")
    

    def get_space_type(self, space_id: str) -> Dict:
        url = f"{self.base_url}/spaces/{space_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json() 
    
    def get_space_by_name(self, space_name: str) -> Dict:

        url = f"{self.base_url}/spaces?type=shared&limit=100"
        response_data = self._get_all_paginated(url)

        for space in response_data:
            if str(space["name"]).lower() == space_name.lower():
                return space
        raise ValueError(f"Space {space_name} not found")

    def get_apps_in_space(self, space_name: str) -> List[Dict]:
        space_id = self.get_space_by_name(space_name)["id"]
        url = f"{self.base_url}/items?resourceType=app&spaceType=shared&spaceId={space_id}&limit=100"

        return self._get_all_paginated(url)
