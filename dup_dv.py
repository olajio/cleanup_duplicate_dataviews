import json
import sys
# import ndjson
import requests
import os
import logging
import argparse
# import subprocess
# from elasticsearch import Elasticsearch
from collections import defaultdict
from argparse import ArgumentParser

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


def get_headers(api_key):
    headers = {
        'kbn-xsrf': 'true',
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {api_key}'
    }
    return headers


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


# Function to retrieve all objects that references any duplicated data views, and count the number of references to each data view
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


# Function to update data view ID in objects referencing duplicated data views
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


# Check of the any object is referencing the Data View to be Deleted
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
    else:
        logging.error(f"Failed to backup data view {data_view_id}. Error: {response.text}")
        sys.exit(1)

# Delete Data View if it has no references by other Kibana Objects
def delete_dataview_if_no_references(data_view_id, all_objects, kibana_url, space_id, headers, dry_run):
    if dry_run:
        logging.info(f"[DRY-RUN] Would check if data view with id: '{data_view_id}' is referenced by any object. If no object is referecning this Data View, it would be deleted")
        return None
    else:
        if not has_references(all_objects, data_view_id):
            dataview_url = f'{kibana_url}/s/{space_id}/api/data_views/data_view/{data_view_id}'
            response = requests.delete(dataview_url, headers=headers)
            if response.status_code == 200:
                print("")
                print(f"Data view with ID {data_view_id} successfully DELETED.")
            else:
                print("")
                print(f"Failed to delete Old data view {data_view_id} . Status code: {response.status_code}, Response: {response.text}")
        else:
            print("")
            print(f"Data view {data_view_id} has references and was NOT deleted.")


# main
def main(kibana_url, headers, space_id, dry_run):
    setup_logging("log_file.log")  # Initialize logging
    updated_objects_count = 0
    data_views_to_be_deleted = []
    objects_config_before_update = []
    updated_objects = []
    all_kibana_objects, num_of_kibana_objects = retrieve_all_kibana_objects(headers, kibana_url)
    export_all_kibana_objects(all_kibana_objects, num_of_kibana_objects, headers, kibana_url, dry_run)
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
            print(f"Title: {title}")
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
            backup_data_view(kibana_url, headers, space_id, data_view_id, f"BData_view_{data_view_id}_back_up.ndjson")
            # Delete each data view
            delete_dataview_if_no_references(data_view_id, all_objects, kibana_url, space_id, headers, dry_run)

    else:
        print("There are no Data Views to be deleted")


if __name__ == "__main__":
    parser = ArgumentParser(description='Automate the process of cleaning up duplicate data views!')
    parser.add_argument('--kibana_url', default='None', required=True)
    parser.add_argument('--api_key', default='None', required=True)
    parser.add_argument('--space_id', default='None', required=True)
    parser.add_argument('--dry_run', choices=['True', 'False', 'false'], default='True')    # Set dry_run=True to test without updating the object
    args = parser.parse_args()
    kibana_url = args.kibana_url
    api_key = args.api_key
    space_id = args.space_id
    dry_run = args.dry_run
    if dry_run.lower() == 'true':
        dry_run = True
    else:
        dry_run = False

    headers = get_headers(api_key)
    main(kibana_url, headers, space_id, dry_run)
