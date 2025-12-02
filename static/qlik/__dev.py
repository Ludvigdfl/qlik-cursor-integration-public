import sys
import os
import time
from qlik_script import QlikScript, _App_id    
App_Name = "Load"
 
print(f"Running remove({App_Name})")
Qlik = QlikScript(os.getenv("Qlik_Climber_API_For_Cursor"),_App_id()[App_Name])

Qlik.get_app_script()
Qlik.get_app_script_by_id()

app_script = Qlik.get_app_script_by_id() 
app_script_tabbed = Qlik.parse_script_tabs(app_script)

Qlik.save_tabs_as_qvs_files(app_script_tabbed)