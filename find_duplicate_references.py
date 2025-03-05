import requests
import json
from collections import defaultdict

# Configuration: Replace these values with your Kibana host, authentication, and desired object type.
KIBANA_HOST = "http://localhost:5601"
USERNAME = "your_username"       # If authentication is required.
PASSWORD = "your_password"       # If authentication is required.
OBJECT_TYPE = "visualization"    # You can change this to any other saved object type.
PAGE_SIZE = 100                  # Number of objects per request.

def find_duplicate_references(saved_object):
    reference_counts = defaultdict(int)
    duplicates = {}
    for ref in saved_object.get("references", []):
        key = (ref.get("type"), ref.get("id"))
        reference_counts[key] += 1
        if reference_counts[key] > 1:
            duplicates[key] = reference_counts[key]
    return duplicates

def get_saved_objects(object_type, page=1, per_page=PAGE_SIZE):
    # Construct the API endpoint URL. The _find endpoint allows pagination.
    url = f"{KIBANA_HOST}/api/saved_objects/_find"
    params = {
        "type": object_type,
        "page": page,
        "per_page": per_page
    }
    headers = {
        "kbn-xsrf": "true",  # Required by Kibana API for non-GET requests and sometimes GET as well.
        "Content-Type": "application/json"
    }
    # If authentication is needed, include HTTP Basic Auth.
    response = requests.get(url, params=params, headers=headers, auth=(USERNAME, PASSWORD))
    response.raise_for_status()
    return response.json()

def scan_saved_objects():
    page = 1
    total = None

    while True:
        data = get_saved_objects(OBJECT_TYPE, page)
        saved_objects = data.get("saved_objects", [])
        if total is None:
            total = data.get("total", 0)
            print(f"Found {total} objects of type '{OBJECT_TYPE}'.")

        for obj in saved_objects:
            duplicates = find_duplicate_references(obj)
            if duplicates:
                print(f"Object ID {obj.get('id')} has duplicate references:")
                for (ref_type, ref_id), count in duplicates.items():
                    print(f"  {ref_type} with id {ref_id} appears {count} times.")

        # Pagination: Check if we've fetched all objects.
        if page * PAGE_SIZE >= total:
            break
        page += 1

if __name__ == "__main__":
    scan_saved_objects()
