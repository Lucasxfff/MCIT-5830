from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
import requests
import json
import time

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.to_checksum_address(bayc_address)

# You will need the ABI to connect to the contract
# The file 'abi.json' has the ABI for the bored ape contract
# In general, you can get contract ABIs from etherscan
# https://api.etherscan.io/api?module=contract&action=getabi&address=0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D
with open('/home/codio/workspace/abi.json', 'r') as f:
    abi = json.load(f)

############################
# Connect to an Ethereum node
api_url = "https://mainnet.infura.io/v3/7569e80fb3444a94af90c292296c313a"  # Replace with your Ethereum node URL
provider = HTTPProvider(api_url)
web3 = Web3(provider)

def get_ape_info(apeID):
    assert isinstance(apeID, int), f"{apeID} is not an int"
    assert 1 <= apeID, f"{apeID} must be at least 1"

    data = {'owner': "", 'image': "", 'eyes': "" }

    # YOUR CODE HERE
    contract = web3.eth.contract(address=contract_address, abi=abi)
    
    # Step 1: Retrieve the owner of the Ape using `ownerOf(apeID)`
    owner = contract.functions.ownerOf(apeID).call()
    data['owner'] = owner

    # Step 2: Retrieve the IPFS URI for the Ape's metadata using `tokenURI(apeID)`
    token_uri = contract.functions.tokenURI(apeID).call()
    ipfs_hash = token_uri.replace("ipfs://", "")  # Remove the IPFS protocol prefix to get the hash only
    ipfs_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"

    # Step 3: Fetch metadata from IPFS and extract `image` and `eyes` attributes
    response = requests.get(ipfs_url)

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

    assert isinstance(data, dict), f'get_ape_info{apeID} should return a dict' 
    assert all([a in data.keys() for a in ['owner', 'image', 'eyes']]), f"return value should include the keys 'owner','image' and 'eyes'"
    return data
