# Documentation on the automation for cleaning up duplicate data views in Kibana:

## Main components and relevant links:

Code repo: https://github.com/olajio/duplicate-dv

The main script: https://github.com/olajio/duplicate-dv/blob/main/cleanup_duplicate_dataviews.py

get_spaces script: https://github.com/olajio/duplicate-dv/blob/main/get_spaces.py
    



## Requirements:

This is a Python script, so you would need to have Python installed on your local machine, as well as any IDE of your choice that could run Python. E.g. Pycharm, VSCode

Ensure you have the permission to install Python Modules on your local machine. This would be needed especially when running this script on your machine for the first time


## Prerequisite:

**Github Personal Access token/Gitlab Project Access Token**: This script uploads some files to Github/Gitlab, so you would need to create a Personal Access Token to authenticate to Github or Project Access Token to Gitlab

**Elastic API Key :** You would require API key in the respective Elastic cluster to allow the API key to have the permission to read, write (update) and delete Kibana objects (data views). See the following for a API permission policy that has been tested to work well in all the Kibana spaces:

```
{
  "ELK-ITSMA-710-Role": {
    "cluster": [
      "all"
    ],
    "indices": [
      {
        "names": [
          "*:*"
        ],
        "privileges": [
          "all"
        ],
        "field_security": {
          "grant": [
            "*"
          ]
        },
        "allow_restricted_indices": true
      }
    ],
    "applications": [
      {
        "application": "kibana-.kibana",
        "privileges": [
          "feature_osquery.all",
          "feature_savedObjectsTagging.all",
          "feature_savedObjectsManagement.all",
          "feature_indexPatterns.all",
          "feature_advancedSettings.all",
          "feature_dev_tools.all",
          "feature_actions.all",
          "feature_stackAlerts.all",
          "feature_fleet.all",
          "feature_siem.all",
          "feature_logs.all",
          "feature_infrastructure.all",
          "feature_apm.all",
          "feature_uptime.all",
          "feature_observabilityCases.all",
          "feature_discover.all",
          "feature_dashboard.all",
          "feature_canvas.all",
          "feature_maps.all",
          "feature_ml.all",
          "feature_graph.all",
          "feature_visualize.all"
        ],
        "resources": [
          "space:*"
        ]
      }
    ],
    "run_as": [
      "*"
    ],
    "metadata": {},
    "transient_metadata": {
      "enabled": true
    }
  }
}
```



**Space Permission :** In addition to the permission of the API key, the target space also needs to have the necessary permissions space. Since the Python script is using data_view and saved_objects API. Ensure that the space has both Data View Management and Saved Objects Management permissions. See the image below showing these permissions highlighted:

![Screenshot 2025-01-21 at 7 14 10 AM](https://github.com/user-attachments/assets/af097cad-45fc-48fb-a8ac-56477b0118e6)




**Local machine admin permission :** Ensure you have the permission to install Python Modules on your local machine. This would be needed especially when running this script on your machine for the first time

## Script parameters:



**--kibana_url** - This is the Kibana URL in the respective deployment. See the following for the respective Kibana URL in our clusters:



kibana_url = "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.us-east-1.aws.found.io:9243"

**--api_key** - this is a key to be used in the api request to elastic; the key needs to be created in the respective target deployment and it should have the relevant permission to read and create kibana objects in every space in the deployment. See the configuration of the api key in the pre-requisites section above


**--cluster_name** - This is the name of the cluster in which the kibana space we're trying to cleanup resides. This parameter is required and acceptable options are: 'dev', 'qa', 'prod', 'ccs'


**--space_id** - This is the id of the target Kibana space, where the duplicated data views is to be cleaned up. Note that it's likely for the id of a space to be different from the name of the space. Make sure to run the command GET kbn:api/spaces/space to retrieve the correct id of the target space. Alternatively, you can run the get_spaces.py script to retrieve the id of the spaces. See the following for sample command to run the `get_spaces.py script: python3 get_spaces.py --kibana_url "<kibana_url>" --api_key "<api_key>" --space_id "<space_id>"`

**--github_username/--gitlab_username** - This is the github/gitlab username of the person running the script. The script uses this to authenticate to github to upload the log files and other kibana object back-up files to github. This parameter is required.



**--github_key/private_token** - A Personal access token is the preferred authentication method to Github when communicating with Github/Gitlab via API. This parameter is required. To generate a Personal Access Token, see the instruction in the following link to [Create Personal Access Token in Gitlab](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) or to create Project Access Token in gitlab, follow this instruction to [Create Project Access Token](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html#create-a-project-access-token)

**--dry_run** - You can optionally choose to dry_run the code and review what changes would be made if the code actually runs. This script implements dry_run only on functions that would potentially make changes Kibana objects or that would potentially delete data views. The script is written to dry_run by default. The dry_run parameter has to be set to False if you want actual changes to be made in the Kibana space.





**Params to the script:**

<img width="838" alt="image" src="https://github.com/user-attachments/assets/ed13d705-faa1-424e-b2a3-7eb907de37d4" />



## Usage:
 

### Python command syntax:

`python3 cleanup_duplicate_dataviews.py --kibana_url "<kibana_url>" --api_key "<api_key>" --cluster_name "<cluster_name>" --space_id "<space_id>" --github_username "<github_username>" --github_key "<github_key>" --dry_run "True"`

### Sample command:

`python3 cleanup_duplicate_dataviews.py --kibana_url "https://XXXXXXXXXXXXXXXXXXXX.us-east-1.aws.found.io:9243" --api_key "XXXXXXXXXXXXHRIbTZ5LVM6bEp5QXXXXXXXXXXRKWVVrUQ==" --cluster_name "dev" --space_id "test_space_ola" --github_username "oolajide" --github_key "ghp_XXXXXXXXXXRKXXXXXXXXXXRK" --dry_run "False"`


### Script Workflow

https://whiteboard.office.com/me/whiteboards/4f84e454-b330-4c89-9993-cf0526167b1d

![image](https://github.com/user-attachments/assets/6c2d395e-d776-492d-a90d-b2a2c3fcf0b8)



### Restore Kibana Objects and Data views to original state:


In the event that something goes wrong while updating the Kibana Objects or Deleting duplicate data views, we can restore the Kibana objects (lens, visualizations, dashboards, maps, data views…) to their states prior to running this script. A file named **kibana_objects.ndjson** is created each time this script is ran. This file is the backup for ALL Kibana objects in the target space and should be used to restore all objects to their original state. Additionally, if the deleted Data views are the only objects that needed to be restored to their original configuration, this script backs specifically backs up the data views right before they're deleted. Each of the Data views is backed in a file with the following name format: **data_view_<data_view_id>_backup.ndjson**. Note that these respective Kibana object files and the log files are also uploaded to the Github branch that is created by the script. So, taking note of the branch is important in case we want to audit the script and or restore objects from the backup files.


### Expected results/Validation:

Once the script is ran, it is expected to cleanup duplicated data view after updating the objects that are referencing those data views with the id of the **“new”** or **“preferred”** data view. So once can either manually validate these in Kibana or rerun the script one more time to ensure that: **“No duplicated Data views found”**, **“No objects needed to be updated”** and **“No Data Views needed to be deleted”**.  When you run the script one more time after the space is cleaned-up, you should expect to see three **ALL CLEAR** messages with the phrases listed above. It should look like the following image:
