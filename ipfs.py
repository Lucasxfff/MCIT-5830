import requests
import json

# Pinata credentials
PINATA_API_KEY = "038e8b9f3220366f832b"
PINATA_SECRET_API_KEY = "1365bf267cdad5244a94a25bea1e6ebde90a28dd753be15c8d17cf43169ca3b5"

def pin_to_ipfs(data):
    assert isinstance(data, dict), f"Error pin_to_ipfs expects a dictionary"

    # Convert the dictionary to a JSON string
    json_data = json.dumps(data)

    # Pinata's pinning endpoint
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"

    # Headers for authentication with Pinata
    headers = {
        'pinata_api_key': PINATA_API_KEY,
        'pinata_secret_api_key': PINATA_SECRET_API_KEY,
    }

    # Pin the file to Pinata's IPFS service
    response = requests.post(url, files={'file': ('data.json', json_data)}, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response and return the CID (IpfsHash)
        cid = response.json()['IpfsHash']
        return cid
    else:
        raise Exception(f"Error pinning to IPFS: {response.text}")

def get_from_ipfs(cid, content_type="json"):
    assert isinstance(cid, str), f"get_from_ipfs accepts a cid in the form of a string"

    # Pinata's public gateway for accessing pinned content
    url = f"https://gateway.pinata.cloud/ipfs/{cid}"

    # Make a GET request to retrieve the data
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON content from the response
        data = json.loads(response.content)
        assert isinstance(data, dict), f"get_from_ipfs should return a dict"
        return data
    else:
        raise Exception(f"Error fetching from IPFS: {response.text}")

if __name__ == "__main__":
    # Test pinning data to IPFS via Pinata
    test_data = {"name": "Bored Ape", "id": 489}
    try:
        cid = pin_to_ipfs(test_data)
        print(f"Data pinned with CID: {cid}")

        # Test retrieving data from IPFS
        fetched_data = get_from_ipfs(cid)
        print(f"Data retrieved from IPFS: {fetched_data}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
