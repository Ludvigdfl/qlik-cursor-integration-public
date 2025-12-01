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


def _App_id() -> str:

    Extract    = "e60b66ef-378d-4976-b8f4-9039796afa23"
    Transform  = "b9cfa507-0024-4c3b-8295-1c344f12e5b7"
    Load       = "f97e7f7c-f090-4892-8185-48ce4448b9a7"
    
    return {
        "Extract": Extract,
        "Transform": Transform,
        "Load": Load
    }


class QlikScript:
    def __init__(self, api_key: str, app_id: str):
        self.api_key = api_key
        self.app_id = app_id
        self.base_url = "https://climber-se.eu.qlikcloud.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        app_name_raw = self.get_app_info()["attributes"]["name"]
        # Sanitize app_name for use in file paths
        self.app_name = re.sub(r'[<>:"/\\|?*]', '_', app_name_raw)
    
    @staticmethod
    def _get_project_root() -> Path:
        """Get the project root directory (where the scripts folder is located)."""
        # Get the directory of this file (static/qlik/)
        current_file = Path(__file__).resolve()
        # Go up two levels to get to project root
        project_root = current_file.parent.parent.parent
        return project_root

    def empty_script_directory(self):
        project_root = self._get_project_root()
        scripts_dir = project_root / "scripts" / self.app_name / self.app_id
        app_dir = project_root / "scripts" / self.app_name
        
        # Remove app_id directory and its contents
        if scripts_dir.exists():
            shutil.rmtree(scripts_dir)

        # Remove app_name directory if empty after removing app_id
        if app_dir.exists() and not any(app_dir.iterdir()):
            app_dir.rmdir()

    def get_app_info(self) -> Dict:
        url = f"{self.base_url}/apps/{self.app_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_app_script(self) -> Dict:
        self.empty_script_directory()
        url = f"{self.base_url}/apps/{self.app_id}/scripts"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        project_root = self._get_project_root()
        versions_dir = project_root / "scripts" / self.app_name / self.app_id / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        script_file = versions_dir / "IDs.json"
        with open(script_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return data
    

    def get_app_script_by_id(self) -> str:
        project_root = self._get_project_root()
        script_file = project_root / "scripts" / self.app_name / self.app_id / "versions" / "IDs.json"
        with open(script_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        scripts_list = data.get("scripts", [])
        if not scripts_list:
            raise ValueError(f"No scripts found in stored file for app {self.app_id}")
        
        script_id = scripts_list[0].get("scriptId")
        if not script_id:
            raise ValueError(f"No scriptId found in the first script entry")
        
        url = f"{self.base_url}/apps/{self.app_id}/scripts/{script_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()["script"]
    
    def parse_script_tabs(self, script: str) -> Dict[str, str]:
        """
        Parse a Qlik script and split it by tab markers (///$tab _NAMEOFTAB_).
        
        Args:
            script: The full Qlik script string
            
        Returns:
            Dictionary mapping tab names to their script content
        """
        # Pattern to match tab markers: ///$tab TABNAME (captures everything until newline)
        tab_pattern = r'///\$tab\s+([^\r\n]+)'
        
        # Find all tab markers and their positions
        matches = list(re.finditer(tab_pattern, script))
        
        if not matches:
            # No tabs found, return as single "Main" tab
            return {"Main": script.strip()}
        
        tabs = {}
        
        # Extract first tab (before first marker)
        first_tab_content = script[:matches[0].start()].strip()
        if first_tab_content:
            tabs["Main"] = first_tab_content
        
        # Extract each tab
        for i, match in enumerate(matches):
            tab_name = match.group(1)
            tab_name = f"{i}___{tab_name}"  # Name with i.__ to keep order of tabs
            start_pos = match.end()
            
            # Find the end position (start of next tab or end of script)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(script)
            
            tab_content = script[start_pos:end_pos].strip()
            tabs[tab_name] = tab_content
        
        
        return tabs


    def save_tabs_as_qvs_files(self, tabs: Dict[str, str]) -> List[str]:
        """
        Save each tab to a separate .qvs file.
        
        Args:
            tabs: Dictionary mapping tab names to script content
            
        Returns:
            List of file paths created
        """
        # Create output directory: scripts/{app_name}/{app_id}
        project_root = self._get_project_root()
        output_dir = project_root / "scripts" / self.app_name / self.app_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        print(f"Reading tabs..")
        for tab_name, content in tabs.items():
            # Sanitize filename (remove invalid characters)
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', tab_name)
            file_path = output_dir / f"{safe_name}.qvs"
            
            # Normalize line endings to \r only (convert \r\n to \r, and \n to \r)
            normalized_content = content.replace('\r\n', '\r').replace('\n', '\r')
            
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                print(f"Tab: {tab_name}")
                f.write(normalized_content)
            
            created_files.append(str(file_path))
        
        return created_files


    def combine_tabs_from_files(self, tab_order: List[str] = None) -> str:
        """
        Combine multiple .qvs files back into a single Qlik script with tab markers.
        
        Args:
            tab_order: Optional list specifying the order of tabs. 
                    If None, files are sorted alphabetically.
                    
        Returns:
            Combined script string with tab markers
        """
        project_root = self._get_project_root()
        scripts_path = project_root / "scripts" / self.app_name / self.app_id
        
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
            # Sort descending based on first 3 characters of filename
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
    

    def parse_script_to_tabs(self) -> Dict[str, str]:
        script_data = self.get_app_script_by_id()
        script_content = script_data.get("script", "")
        tabs = self.parse_script_tabs(script_content)
        
        self.save_tabs_to_files(tabs)
        
        return tabs

    def get_app_script_tabbed(self) -> str:
        project_root = self._get_project_root()
        script_dir = project_root / "scripts" / self.app_name / self.app_id
        
        if not script_dir.exists():
            raise ValueError(f"Directory {script_dir} does not exist")
        
        qvs_files = list(script_dir.glob("*.qvs"))
        if not qvs_files:
            raise ValueError(f"No .qvs files found in {script_dir}")
        
        ordered_files = sorted(qvs_files, key=lambda x: x.stem[:3] if len(x.stem) >= 3 else x.stem, reverse=False)
        
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

    def set_app_script(self, app_script_string: str, version_message: str = "test") -> Dict:
        payload = {
            "script": app_script_string,
            "versionMessage": version_message
        }
        
        project_root = self._get_project_root()
        script_json_path = project_root / "scripts" / f"{self.app_name}/{self.app_id}.json"
        with open(script_json_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        url = f"{self.base_url}/apps/{self.app_id}/scripts"
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response

    def reload_app(self, weight: int = 1, partial: bool = False) -> str:
        url = f"{self.base_url}/reloads"
        payload = {
            "appId": self.app_id,
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
    
    