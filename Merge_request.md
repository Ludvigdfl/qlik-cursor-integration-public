
We will merge the current class qlik_masteritems into the existing repo.

The repo we are merging into is focused on the qlik scripting part.
It can curently get/set/load ... the script from a qlik cloud app (writing the logic in qlik_script.py and then expose this in qlik.py)

Your job is to 
Make a small adjustment to the qlik-script part and then merge the qlik-masteritems into the qlik-script solution to make use of the same api-key + tenanturl.

1. 
Instead of storing/reading the scripts in "scripts/app-id/app-name/tabs1.qvs" do it from
"Apps/app-id/app-name/script/tabs1.qvs". 
This will allow us to store the qlik-masteritems into the same logical place "Apps/app-id/app-name/masteritems/measures.json".

2. 
Adjust the init in qlik_masteritems.py so that it sets the api-key and tenant-url the same way as qlik_script.py does.
Thereby also removing the current setting in lines 399 to 402.

3. 
Add the following 4 functions to qlik.py (mimicing the current methods like get() or set()...) 
* get_masterdimensions()
* set_masterdimensions()
* get_mastermeasures()
* set_mastermeasures()

4. 
Finally add the new functions to the cli logic from line 141 and downward.