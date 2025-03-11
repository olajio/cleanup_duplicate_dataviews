import requests
import json

# Configuration: Update these to match your environment.
KIBANA_HOST = "http://localhost:5601"
USERNAME = "your_username"
PASSWORD = "your_password"
OBJECT_TYPE = "search"         # Change this if you want to target a different object type.
PAGE_SIZE = 100                # Number of objects per API page

# The old and new data view IDs.
old_data_view_id = "d1e912b0-958c-4307-ae6e-9d9da63b00ea"
new_data_view_id = "ABC1234"

def update_references(saved_object, old_id, new_id):
    """
    Scans the references list in the saved object and updates the id
    for any reference where:
      - reference.type is "index-pattern"
      - reference.id equals old_id
    Returns a tuple (updated, new_references) where:
      - updated is True if any reference was modified.
      - new_references is the updated list of references.
    """
    updated = False
    new_refs = []
    for ref in saved_object.get("references", []):
        if ref.get("type") == "index-pattern" and ref.get("id") == old_id:
            new_ref = ref.copy()  # Copy to preserve the original structure.
            new_ref["id"] = new_id
            updated = True
            new_refs.append(new_ref)
        else:
            new_refs.append(ref)
    return updated, new_refs

def get_saved_objects(object_type, page=1, per_page=PAGE_SIZE):
    url = f"{KIBANA_HOST}/api/saved_objects/_find"
    params = {
        "type": object_type,
        "page": page,
        "per_page": per_page
    }
    headers = {
        "kbn-xsrf": "true",
        "Content-Type": "application/json"
    }
    response = requests.get(url, params=params, headers=headers, auth=(USERNAME, PASSWORD))
    response.raise_for_status()
    return response.json()

def update_saved_object(obj_type, obj_id, updated_references):
    url = f"{KIBANA_HOST}/api/saved_objects/{obj_type}/{obj_id}"
    headers = {
        "kbn-xsrf": "true",
        "Content-Type": "application/json"
    }
    payload = {
        "references": updated_references
    }
    response = requests.put(url, headers=headers, auth=(USERNAME, PASSWORD), data=json.dumps(payload))
    response.raise_for_status()
    return response.json()

def scan_and_update_saved_objects():
    page = 1
    total = None
    updated_count = 0

    while True:
        data = get_saved_objects(OBJECT_TYPE, page)
        saved_objects = data.get("saved_objects", [])
        if total is None:
            total = data.get("total", 0)
            print(f"Found {total} objects of type '{OBJECT_TYPE}'.")

        for obj in saved_objects:
            obj_id = obj.get("id")
            updated, new_refs = update_references(obj, old_data_view_id, new_data_view_id)
            if updated:
                print(f"Updating object {obj_id} with new data view id...")
                update_resp = update_saved_object(OBJECT_TYPE, obj_id, new_refs)
                print(f"Updated object {obj_id}: {update_resp}")
                updated_count += 1

        if page * PAGE_SIZE >= total:
            break
        page += 1

    print(f"Finished. Updated {updated_count} objects.")

if __name__ == "__main__":
    scan_and_update_saved_objects()
