import sys
import requests
import logging
from collections import defaultdict
from argparse import ArgumentParser
from datetime import datetime
import pytz
import os
import base64


# Set up timestamp in EST
def set_timestamp():
    """Sets up a log file with the creation timestamp in its name using EST time."""
    # Define the EST timezone
    est_tz = pytz.timezone("US/Eastern")

    # Get the current timestamp in EST
    timestamp = datetime.now(est_tz).strftime("%Y_%m_%d-%H_%M_%S")
    return timestamp

# Setup Log file
def setup_log_file(timestamp):
    # Create the log file name with the EST timestamp
    log_file_name = f"log_file_{timestamp}.log"
    return log_file_name


# Configures logging to redirect logs and print statements to a custom log file
def setup_logging(log_file="output.log"):
    """
    Configures logging to redirect logs and print statements to a custom log file.
    Overwrites the log file on each run.

    Args:
        log_file (str): The name of the log file.
    """
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),  # Overwrite log file each run
            logging.StreamHandler(sys.stdout),  # Print logs to stdout
        ],
    )

    # Redirect print statements to logging
    sys.stdout = LoggerWriter(logging.getLogger(), logging.INFO)
    sys.stderr = LoggerWriter(logging.getLogger(), logging.ERROR)


class LoggerWriter:
    """
    A file-like object to redirect print statements to the logging system.

    Args:
        logger (logging.Logger): Logger instance to write to.
        log_level (int): Logging level for the messages.
    """
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level

    def write(self, message):
        if message.strip():  # Ignore empty messages
            self.logger.log(self.log_level, message.strip())

    def flush(self):
        pass  # No action needed for flush


# Set up headers for Kibana authentication
def get_headers(api_key):
    headers = {
        'kbn-xsrf': 'true',
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {api_key}'
    }
    return headers


# Check-in files to a new github branch
def upload_file_to_github(repo_url, github_username, github_key, local_file_path, repo_file_path, github_branch, timestamp):
    """
    Upload or update a file in a GitHub repository.

    Args:
        repo_url (str): The GitHub repository URL.
        username (str): GitHub username.
        password (str): GitHub account password (or Personal Access Token).
        file_path (str): Path to the local file to be uploaded.
        repo_file_path (str): Path in the repository where the file should be saved.
        commit_message (str): Commit message for the file upload.
        branch (str): The branch where the file should be committed. Default is 'main'.
    """

    commit_message = f"Uploaded object via script at {timestamp}"

    # Extract repo details from the URL
    repo = repo_url.split("https://github.com/")[1]
    api_url = f"https://github.com/api/v3/repos/{repo}"

    # Step 1: Get the default branch's SHA
    repo_info_url = f"{api_url}"
    print(f"repo_info_url : {repo_info_url}")
    repo_info_response = requests.get(repo_info_url, auth=(github_username, github_key))
    if repo_info_response.status_code != 200:
        print(f"Error retrieving repository info: {repo_info_response.status_code} : {repo_info_response.text}")
        raise Exception("Failed to retrieve repository information.")

    default_branch = repo_info_response.json().get("default_branch", "main")
    default_branch_url = f"{api_url}/git/ref/heads/{default_branch}"
    default_branch_response = requests.get(default_branch_url, auth=(github_username, github_key))
    if default_branch_response.status_code != 200:
        print(f"Error retrieving default branch '{default_branch}': {default_branch_response.text}")
        raise Exception("Default branch not found.")

    default_branch_sha = default_branch_response.json()["object"]["sha"]

    # Step 2: Create the new branch
    create_branch_url = f"{api_url}/git/refs"
    payload = {
        "ref": f"refs/heads/{github_branch}",
        "sha": default_branch_sha
    }
    create_branch_response = requests.post(create_branch_url, json=payload, auth=(github_username, github_key))
    if create_branch_response.status_code == 201:
        print(f"Branch '{github_branch}' created successfully.")
    else:
        print(f"Failed to create branch: {create_branch_response.status_code}, {create_branch_response.text}")
        raise Exception(f"Failed to create branch: {create_branch_response.text}")

    # Step 3: Read the local file and encode it
    with open(local_file_path, "rb") as file:
        content = base64.b64encode(file.read()).decode("utf-8")

    # Step 4: Prepare the payload for file upload
    file_url = f"{api_url}/contents/{repo_file_path}"
    payload = {
        "message": commit_message,
        "content": content,
        "branch": github_branch  # Specify the branch
    }

    # Step 5: Upload the file
    response = requests.put(file_url, json=payload, auth=(github_username, github_key))
    if response.status_code in (200, 201):
        print(f"File successfully uploaded to '{repo_url}/{repo_file_path}' on branch '{github_branch}'.")
    else:
        print(f"Failed to upload file: {response.status_code}, {response.text}")


# Check-in files to an existing github branch
def upload_file_to_existing_github(repo_url, github_username, github_key, local_file_path, repo_file_path, github_branch, timestamp):
    """
    Upload or update a file in a GitHub repository on the specified branch.

    Args:
        repo_url (str): The GitHub repository URL.
        github_username (str): GitHub username.
        github_key (str): GitHub account password or Personal Access Token.
        file_path (str): Local path to the file to be uploaded.
        repo_file_path (str): Path in the repository where the file should be saved.
        commit_message (str): Commit message for the upload.
        branch (str): The branch where the file should be committed.
    """
    # Commit message
    commit_message = f"Log file uploaded via script at {timestamp}"

    # Parse repository owner and name from the URL
    repo = repo_url.split("https://github.com/")[1]
    api_url = f"https://github.com/api/v3/repos/{repo}/contents/{repo_file_path}"

    # Read the local file and encode it
    with open(local_file_path, "rb") as file:
        content = base64.b64encode(file.read()).decode("utf-8")

    # Prepare payload for file upload
    payload = {
        "message": commit_message,
        "content": content,
        "branch": github_branch
    }

    # Upload or update the file
    response = requests.put(api_url, json=payload, auth=(github_username, github_key))
    if response.status_code in (200, 201):
        print(f"File successfully uploaded to '{repo_url}/{repo_file_path}' on branch '{github_branch}'.")
    else:
        print(f"Failed to upload file: {response.status_code}, {response.text}")


# Retrieve all kibana objects in the current space
def retrieve_all_kibana_objects(headers, kibana_url):
    logging.info(f"Retrieving all Kibana objects in space: '{space_id}'...")
    find_objects_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_find"
    object_type = ["config", "config-global", "url", "index-pattern", "action", "query", "tag", "graph-workspace",
                   "alert", "search", "visualization", "event-annotation-group", "dashboard", "lens", "cases",
                   "metrics-data-source", "links", "canvas-element", "canvas-workpad", "osquery-saved-query",
                   "osquery-pack", "csp-rule-template", "map", "infrastructure-monitoring-log-view",
                   "threshold-explorer-view", "uptime-dynamic-settings", "synthetics-privates-locations", "apm-indices",
                   "infrastructure-ui-source", "inventory-view", "infra-custom-dashboards", "metrics-explorer-view",
                   "apm-service-group", "apm-custom-dashboards"]
    all_kib_objects = []
    page = 1
    for type in object_type:
        params = {
            #'fields': 'references',
            'type': type,
            'per_page': 10000
        }
        response = requests.get(find_objects_endpoint, headers=headers, params=params, verify=True)
        if response.status_code == 200:
            # response.raise_for_status()
            data = response.json()
            data = data.get("saved_objects", [])
            all_kib_objects.extend([{"id": obj["id"], "type": obj["type"]} for obj in data])
        else:
            logging.error(f"Failed to retrieve Kibana objects. Status code: {response.status_code}, Response: : {get_response.text}")

    num_of_kibana_objects = len(all_kib_objects)
    logging.info(f"{num_of_kibana_objects} Kibana objects were found in this space: '{space_id}'")
    if num_of_kibana_objects == 0:
        print(f"There are NO Kibana objects in this space: '{space_id}'. No Further action is needed!")
        print(f"Exiting...")
        sys.exit(0)
    return all_kib_objects, num_of_kibana_objects


# Export all Kibana objects using the Saved Objects API and save to an NDJSON file.
def export_all_kibana_objects(all_kibana_objects, num_of_kibana_objects, headers, kibana_url, dry_run):
    export_objects_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_export"
    OUTPUT_FILE = "kibana_objects.ndjson"  # Path to save the exported objects
    logging.info(f"Exporting all Kibana objects in space: '{space_id}' to the '{OUTPUT_FILE}'. This would be used to restore all objects in case something goes wrong...")
    if dry_run:
        logging.info(f"[DRY-RUN] Would Export all Kibana objects in this space: '{space_id}' using the Saved Objects API and save to an NDJSON file: '{OUTPUT_FILE}'")
    else:
        if num_of_kibana_objects > 0:
            payload = {
                "objects": all_kibana_objects,
                "includeReferencesDeep": True
            }
            response = requests.post(export_objects_endpoint, headers=headers, json=payload)
            if response.status_code == 200:
                with open(OUTPUT_FILE, "w") as file:
                    file.write(response.text)
                logging.info(f"All {num_of_kibana_objects} Kibana objects are successfully backed-up to the '{OUTPUT_FILE}' file")
            else:
                logging.error(f"Failed to export objects. Status code: {response.status_code}, Response: : {get_response.text}")
        else:
            logging.info(f"There are no Kibana objects to back-up. The '{OUTPUT_FILE}' file is not updated")
        return OUTPUT_FILE


# Function to get all data views in the space ID specified
def get_all_dataviews(space_id, headers, kibana_url):
    dataview_url = f'{kibana_url}/s/{space_id}/api/data_views'
    response = requests.get(dataview_url, headers=headers, verify=True)
    if response.status_code == 200:
        response = response.json()
        data_views = response['data_view']
    else:
        logging.error(f"Failed to GET all Data Views . Status code: {response.status_code}, Response: : {get_response.text}")
    return data_views


# Function to find duplicated data views by title
def find_duplicated_data_views(data_views):
    title_to_ids = defaultdict(list)
    for data_view in data_views:
        title = data_view["title"]
        id = data_view["id"]
        title_to_ids[title].append(id)
    duplicates = {title: ids for title, ids in title_to_ids.items() if len(ids) > 1}
    return duplicates


# Retrieve all objects that references any duplicated data views, and count the number of references to each data view
def get_object_references(data_view_ids, kibana_url, space_id, headers):
    objects_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_find"
    reference_counts = defaultdict(int)
    object_type = ["config", "config-global", "url", "index-pattern", "action", "query", "tag", "graph-workspace",
                   "alert", "search", "visualization", "event-annotation-group", "dashboard", "lens", "cases",
                   "metrics-data-source", "links", "canvas-element", "canvas-workpad", "osquery-saved-query",
                   "osquery-pack", "csp-rule-template", "map", "infrastructure-monitoring-log-view",
                   "threshold-explorer-view", "uptime-dynamic-settings", "synthetics-privates-locations", "apm-indices",
                   "infrastructure-ui-source", "inventory-view", "infra-custom-dashboards", "metrics-explorer-view",
                   "apm-service-group", "apm-custom-dashboards"]

    all_objects = []
    for type in object_type:
        params = {
            'fields': 'references',
            'type': type,
            'per_page': 10000
        }
        response = requests.get(objects_endpoint, headers=headers, params=params, verify=True)
        response.raise_for_status()
        data = response.json()
        all_objects.extend(data.get("saved_objects", []))

    # Count each object's link to a data view
    for object in all_objects:
        references = object.get("references", [])
        for ref in references:
            if ref["type"] == "index-pattern" and ref["id"] in data_view_ids:
                reference_counts[ref["id"]] += 1
    return reference_counts, all_objects


# Update data view ID in objects referencing duplicated data views
def update_references(ref_type, ref_name, object_type, object_id, old_data_view_id, new_data_view_id, kibana_url, headers, dry_run):
    if dry_run:
        logging.info(f"[DRY-RUN] Would update data view ID in {object_type} with ID: {object_id} from {old_data_view_id} to {new_data_view_id}")
    else:
        object_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/{object_type}/{object_id}"
        update_payload = {
            "references": [
                {
                    "type": ref_type,
                    "id": new_data_view_id,
                    "name": ref_name
                }
            ],
            "attributes": {}
        }
        response = requests.put(object_endpoint, headers=headers, json=update_payload)
        #response.raise_for_status()  # Raise an error if the request failed
        if response.status_code == 200:
            logging.info(f"Updated data view ID in {object} from {old_data_view_id} to {new_data_view_id}")
            updated_kibana_object = response.json()
            print(f"Successfully updated data view ID for object type {object_type} with ID {object_id}.")
            print(f"Old Data View ID: {old_data_view_id}")
            print(f"New Data View ID: {new_data_view_id}")
            return updated_kibana_object
        else:
            logging.error(f"Failed to update object . Status code: {response.status_code}, Response: : {get_response.text}")


# Check if the any object is referencing the Data View to be Deleted
def has_references(all_objects, data_view_id):
    for object in all_objects:
        references = object.get("references", [])
        for ref in references:
            if ref['type'] == 'index-pattern' and ref['id'] in data_view_id:
                return True
    return False



def backup_data_view(kibana_url, headers, space_id, data_view_id, output_file):
    export_objects_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_export"
    payload = {
        "objects": [
            {
                "id": data_view_id,
                "type": "index-pattern"
            }
        ],
        "includeReferencesDeep": True
    }

    response = requests.post(export_objects_endpoint, headers=headers, json=payload)

    if response.status_code == 200:
        # Write the backup data to a file (one for each data view)
        with open(f"data_view_{data_view_id}_backup.ndjson", "w") as file:
            file.write(response.text)
        logging.info(f"Backup successful for data view: '{data_view_id}'! Saved to: 'data_view_{data_view_id}_backup.ndjson'")

        # # Check-in data views to Github
        # dataview_local_file = f"data_view_{data_view_id}_backup.ndjson"
        # dataview_repo_file_path = dataview_local_file
        # upload_file_to_existing_github(repo_url, github_username, github_key, dataview_local_file, dataview_repo_file_path,
        #                                github_branch, timestamp)
    else:
        logging.error(f"Failed to backup data view {data_view_id}. Error: {response.text}")
        sys.exit(1)


# Delete Data View if it has no references by other Kibana Objects
def delete_dataview_if_no_references(data_view_id, all_objects, kibana_url, space_id, headers, dry_run):
    if dry_run:
        logging.info(f"[DRY-RUN] Would check if data view with id: '{data_view_id}' is referenced by any object. If no object is referecning this Data View, you would be prompted to choose if you want it deleted.")
        delete_data_view = input(f"Do you want this Data View with ID: {data_view_id} to be DELETED? Enter 'Y' for Yes, 'N' for No: ").upper()
        if delete_data_view == "Y":
            print(f"[DRY-RUN] Data View with ID: {data_view_id} would be DELETED \n")
        elif delete_data_view == "N":
            print(f"[DRY-RUN] Data View with ID: {data_view_id} would NOT be deleted \n")
        else:
            print(f"Invalid Entry. Re-run script and Enter 'Y' or 'N'")
        return None
    else:
        if not has_references(all_objects, data_view_id):
            dataview_url = f'{kibana_url}/s/{space_id}/api/data_views/data_view/{data_view_id}'
            delete_data_view = input(f"Do you want this Data View with ID: {data_view_id} to be DELETED? Enter 'Y' for Yes, 'N' for No: ").upper()
            if delete_data_view == "Y":
                response = requests.delete(dataview_url, headers=headers)
                if response.status_code == 200:
                    print("")
                    print(f"Data view with ID {data_view_id} successfully DELETED.")
                else:
                    print("")
                    print(f"Failed to delete Old data view {data_view_id} . Status code: {response.status_code}, Response: {response.text}")
            elif delete_data_view == "N":
                print(f"You elected NOT to delete Data View with ID: {data_view_id}. Hence this Data View would NOT be deleted \n")
            else:
                print(f"Invalid Entry. Re-run script and Enter a valid entry: 'Y' or 'N'")
            return None
        else:
            print("")
            print(f"Data view {data_view_id} has references and was NOT deleted.")


# main
def main(kibana_url, headers, space_id, dry_run):
    print(f"Running the script for space: '{space_id}' in the cluster: '{cluster_name}'")

    log_file_name = setup_log_file(timestamp)
    setup_logging(log_file_name)  # Initialize logging
    updated_objects_count = 0
    data_views_to_be_deleted = []
    objects_config_before_update = []
    updated_objects = []

    all_kibana_objects, num_of_kibana_objects = retrieve_all_kibana_objects(headers, kibana_url)
    kibana_objects = export_all_kibana_objects(all_kibana_objects, num_of_kibana_objects, headers, kibana_url, dry_run)
    local_file_path = f"{kibana_objects}"
    repo_file_path = f"all_objects/{local_file_path}"
    upload_file_to_github(repo_url, github_username, github_key, local_file_path, repo_file_path, github_branch, timestamp)
    data_views = get_all_dataviews(space_id, headers, kibana_url)
    duplicates = find_duplicated_data_views(data_views)
    print("")
    if not duplicates:
        logging.info("No duplicated data views found.")
    else:
        dup_data_view_ids = []
        logging.warning("Duplicated data views found:")
        for title, ids in duplicates.items():
            # Get the reference counts for each data view ID in the duplicated group
            reference_counts, all_objects = get_object_references(ids, kibana_url, space_id, headers)
            print(f"DATA VIEW TITLE: {title}")
            for id in ids:
                print(f"  ID: {id}  : {reference_counts[id]}")
                dup_data_view_ids.append(id)
                most_referenced_id = max(reference_counts, key=reference_counts.get)
                if id != most_referenced_id:
                    data_views_to_be_deleted.append(id)
                    for object in all_objects:
                        object_references = object.get("references", [])
                        for ref in object_references:
                            if ref["id"] == id:
                                object_type = object['type']
                                object_id = object['id']
                                old_data_view_id = ref["id"]
                                ref_type = ref["type"]
                                ref_name = ref["name"]
                                new_data_view_id = most_referenced_id
                                print("")
                                update_references(ref_type, ref_name, object_type, object_id, old_data_view_id, new_data_view_id, kibana_url, headers, dry_run)
                                updated_objects.append(object)
                                print("")
                                print("")
                                updated_objects_count += 1
            print("")

    print("")
    if updated_objects:
        if dry_run:
            logging.info("[DRY-RUN] The following objects would be updated:")
            for object in updated_objects:
                print(object)
            print("")
            print(f"[DRY-RUN] {updated_objects_count} objects would have been UPDATED if this code actually ran")
            print("")
        else:
            print("The following objects were updated:")
            for object in updated_objects:
                print(object)
            print("")
            print(f"{updated_objects_count} objects in total were UPDATED")
            print("")
    else:
        print("No objects were updated")
        print("")
    if duplicates:
        print("REVIEW DUPLICATE DATA VIEWS BEFORE REMOVING DUPLICATES WITH ZERO REFERENCES")
        for title, ids in duplicates.items():
            # Get the reference counts for each data view ID in the duplicated group
            reference_counts, all_objects = get_object_references(ids, kibana_url, space_id, headers)
            print(f"Title: {title}")
            for id in ids:
                print(f"  ID: {id}  : {reference_counts[id]}")
                dup_data_view_ids.append(id)
            print("")
    print("")
    if data_views_to_be_deleted:
        logging.warning("ID of Data views to be deleted:")
        print(data_views_to_be_deleted)
        try:
            data_views_to_be_deleted
        except NameError:
            print("")
            data_views_to_be_deleted = []
        for data_view_id in data_views_to_be_deleted:
            # Backup each data view
            backup_data_view(kibana_url, headers, space_id, data_view_id, f"Data_view_{data_view_id}_back_up.ndjson")

            # Check-in data views back-ups to Github
            dataview_local_file = f"data_view_{data_view_id}_backup.ndjson"
            dataview_repo_file_path = dataview_local_file
            upload_file_to_existing_github(repo_url, github_username, github_key, dataview_local_file, dataview_repo_file_path, github_branch, timestamp)

            # Delete each data view
            delete_dataview_if_no_references(data_view_id, all_objects, kibana_url, space_id, headers, dry_run)

    else:
        print("There are no Data Views to be deleted")
    # log_file_name = setup_log_file(timestamp)
    log_file = log_file_name
    log_repo_file_path = log_file
    upload_file_to_existing_github(repo_url, github_username, github_key, log_file, log_repo_file_path, github_branch, timestamp)


if __name__ == "__main__":
    parser = ArgumentParser(description='Automate the process of cleaning up duplicate data views!')
    parser.add_argument('--kibana_url', default='None', required=True)
    parser.add_argument('--api_key', default='None', required=True)
    parser.add_argument('--cluster_name', default='None', choices=['dev', 'qa', 'prod', 'ccs'], required=True)
    parser.add_argument('--space_id', default='None', required=True)
    parser.add_argument('--dry_run', choices=['True', 'False', 'false'], default='True')

    parser.add_argument('--github_username', default='None', required=False)
    parser.add_argument('--github_key', default='None', required=False)

    args = parser.parse_args()
    kibana_url = args.kibana_url
    api_key = args.api_key
    cluster_name = args.cluster_name
    space_id = args.space_id
    dry_run = args.dry_run

    github_username = args.github_username
    github_key = args.github_key

    if dry_run.lower() == 'true':
        dry_run = True
    else:
        dry_run = False

    # Get timestamp
    timestamp = set_timestamp()

    repo_url = "https://github.com/olajio/cleanup_duplicate_dataviews"
    github_branch = f"{github_username}-{timestamp}"

    headers = get_headers(api_key)
    main(kibana_url, headers, space_id, dry_run)
