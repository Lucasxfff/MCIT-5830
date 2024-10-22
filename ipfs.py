import requests
import json

def pin_to_ipfs(data):
    assert isinstance(data, dict), f"Error pin_to_ipfs expects a dictionary"

    # Convert the dictionary to a JSON string
    json_data = json.dumps(data)

    # Infura's IPFS pinning endpoint
    url = "https://ipfs.infura.io:5001/api/v0/add"

    # Infura credentials (you may need to provide your own project ID and secret)
    headers = {
        'Content-Type': 'application/json',
    }

    # Make a POST request to Infura's API
    response = requests.post(url, files={'file': json_data}, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response and return the CID (hash)
        cid = response.json()['Hash']
        return cid
    else:
        raise Exception(f"Error pinning to IPFS: {response.text}")

def get_from_ipfs(cid, content_type="json"):
    assert isinstance(cid, str), f"get_from_ipfs accepts a cid in the form of a string"

    # Infura's IPFS retrieval endpoint
    url = f"https://ipfs.infura.io:5001/api/v0/cat?arg={cid}"

    # Make a POST request to retrieve the data
    response = requests.post(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON content from the response
        data = json.loads(response.content)
        assert isinstance(data, dict), f"get_from_ipfs should return a dict"
        return data
    else:
        raise Exception(f"Error fetching from IPFS: {response.text}")

if __name__ == "__main__":
    # Test pinning data to IPFS
    test_data = {"name": "Bored Ape", "id": 489}
    try:
        cid = pin_to_ipfs(test_data)
        print(f"Data pinned with CID: {cid}")

        # Test retrieving data from IPFS
        fetched_data = get_from_ipfs(cid)
        print(f"Data retrieved from IPFS: {fetched_data}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
