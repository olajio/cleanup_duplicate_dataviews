# Documentation on the automation for cleaning up duplicate data views in Kibana:

## Main components and relevant links:

Code repo: https://github.com/olajio/duplicate-dv

The main script: https://github.com/olajio/duplicate-dv/blob/main/cleanup_duplicate_dataviews.py

get_spaces script: https://github.com/olajio/duplicate-dv/blob/main/get_spaces.py
    



## Requirements:

This is a Python script, so you would need to have Python installed on your local machine, as well as any IDE of your choice that could run Python. E.g. Pycharm, VSCode

Ensure you have the permission to install Python Modules on your local machine. This would be needed especially when running this script on your machine for the first time

## Script parameters:



--kibana_url - This is the Kibana URL in the respective deployment. See the following for the respective Kibana URL in our clusters:



kibana_url = "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.us-east-1.aws.found.io:9243"

--api_key - this is a key to be used in the api request to elastic; the key needs to be created in the respective target deployment and it should have the relevant permission to read and create kibana objects in every space in the deployment. See the configuration of the api key in the pre-requisites section above



--space_id - This is the id of the target Kibana space, where the duplicated data views is to be cleaned up. Note that it's likely for the id of a space to be different from the name of the space. Make sure to run the command GET kbn:api/spaces/space to retrieve the correct id of the target space. Alternatively, you can run the get_spaces.py script to retrieve the id of the spaces. See the following for sample command to run the get_spaces.py script: python3 get_spaces.py --kibana_url "<kibana_url>" --api_key "<api_key>" --space_id "<space_id>"



--dry_run - You can optionally choose to dry_run the code and review what changes would be made if the code actually runs. This script implements dry_run only on functions that would potentially make changes Kibana objects or that would potentially delete data views. The script is written to dry_run by default. The dry_run parameter has to be set to False if you want actual changes to be made in the Kibana space.





Params to the script:

<img width="869" alt="image" src="https://github.com/user-attachments/assets/7a1257ce-b07e-4b31-8caa-69ae6f4fa4a0" />










    
## Usage:
 

### Python command syntax:

python3 delete_duplicate_data_view.py --kibana_url "<kibana_url>" --api_key "<api_key>" --space_id "<space_id>" --dry_run "True"


### Sample command:

python3 cleanup_duplicate_dataviews.py --kibana_url "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.us-east-1.aws.found.io:9243" --api_key "XXXXXXXXXXXXHRIbTZ5LVM6bEp5QXXXXXXXXXXRKWVVrUQ==" --space_id "test_space_ola" --dry_run "True"


### Script Workflow

![image](https://github.com/user-attachments/assets/f9142df7-c5b2-4b5f-81d0-e6913561f96b)



### Restore Kibana Objects and Data views to original state:


In the event that something goes wrong while updating the Kibana Objects or Deleting duplicate data views, we can restore the Kibana objects (lens, visualizations, dashboards, maps, data views…) to their states prior to running this script. A file named kibana_objects.ndjson is created each time this script is ran. This file is the backup for ALL Kibana objects in the target space and should be used to restore all objects to their original state. Additionally, if the deleted Data views are the only objects that needed to be restored to their original configuration, this script backs specifically backs up the data views right before they're deleted. Each of the Data views is backed in a file with the following name format: data_view_<data_view_id>_backup.ndjson.
