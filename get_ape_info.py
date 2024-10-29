from web3 import Web3
from web3.providers.rpc import HTTPProvider
import requests
import json

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.toChecksumAddress(bayc_address)

# Load the ABI for the Bored Ape Yacht Club contract
with open('/home/codio/workspace/abi.json', 'r') as f:
    abi = json.load(f)

# Connect to an Ethereum node (provide the URL of your Ethereum node, e.g., Infura)
api_url = "https://mainnet.infura.io/v3/7569e80fb3444a94af90c292296c313a"
provider = HTTPProvider(api_url)
web3 = Web3(provider)
assert web3.is_connected(), "Failed to connect to Ethereum node"

# Instantiate the contract object
contract = web3.eth.contract(address=contract_address, abi=abi)

# Pinata credentials and gateway
PINATA_API_KEY = "038e8b9f3220366f832b"
PINATA_SECRET_API_KEY = "1365bf267cdad5244a94a25bea1e6ebde90a28dd753be15c8d17cf43169ca3b5"
PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs/"

def get_ape_info(apeID):
    assert isinstance(apeID, int), f"{apeID} is not an int"
    assert 1 <= apeID <= 9999, f"{apeID} must be between 1 and 9999"

    data = {'owner': "", 'image': "", 'eyes': ""}

    # Step 1: Retrieve the owner of the Ape using `ownerOf(apeID)`
    owner = contract.functions.ownerOf(apeID).call()
    data['owner'] = owner

    # Step 2: Retrieve the IPFS URI for the Ape's metadata using `tokenURI(apeID)`
    token_uri = contract.functions.tokenURI(apeID).call()
    ipfs_hash = token_uri.replace("ipfs://", "")  # Remove the IPFS protocol prefix to get the hash only
    ipfs_url = f"{PINATA_GATEWAY}{ipfs_hash}"

    # Step 3: Fetch metadata from IPFS and extract `image` and `eyes` attributes
    response = requests.get(ipfs_url, headers={
        'pinata_api_key': PINATA_API_KEY,
        'pinata_secret_api_key': PINATA_SECRET_API_KEY
    })

    if response.status_code == 200:
        metadata = response.json()
        data['image'] = metadata.get("image", "")

        # Find the "eyes" attribute in the metadata attributes list
        for attribute in metadata.get("attributes", []):
            if attribute.get("trait_type") == "Eyes":
                data['eyes'] = attribute.get("value", "")
                break
    else:
        raise Exception(f"Failed to fetch metadata from IPFS: {response.text}")

    # Ensure data contains the correct keys and types
    assert isinstance(data, dict), f'get_ape_info({apeID}) should return a dict'
    assert all([a in data.keys() for a in ['owner', 'image', 'eyes']]), "Return value should include keys 'owner', 'image', and 'eyes'"
    return data
