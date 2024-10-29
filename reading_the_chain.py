import random
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.providers.rpc import HTTPProvider

# Connection to Ethereum Mainnet
def connect_to_eth():
    url = "https://mainnet.infura.io/v3/7569e80fb3444a94af90c292296c313a"  # Infura URL
    w3 = Web3(HTTPProvider(url))
    assert w3.is_connected(), f"Failed to connect to provider at {url}"
    print("Connected to Ethereum Mainnet")
    return w3

# Connection to BNB Testnet and MerkleValidator Contract
def connect_with_middleware(contract_json):
    with open(contract_json, "r") as f:
        d = json.load(f)
        d = d['bsc']
        address = d['address']
        abi = d['abi']

    url = "https://bsc-testnet.blockpi.network/v1/rpc/public"  # BNB testnet URL
    w3 = Web3(HTTPProvider(url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    assert w3.is_connected(), f"Failed to connect to provider at {url}"
    print("Connected to BNB Testnet")

    contract = w3.eth.contract(address=address, abi=abi)
    return w3, contract

# Part 1: Check if transactions in a block are ordered by priority fee
def is_ordered_block(w3, block_num):
    """
    Takes a block number and returns a boolean indicating whether all transactions in the block are ordered by priority fee.
    """
    block = w3.eth.get_block(block_num, full_transactions=True)
    base_fee = block.get('baseFeePerGas', 0)  # Use 0 for pre-EIP-1559 blocks

    previous_fee = None
    for tx in block.transactions:
        if 'maxPriorityFeePerGas' in tx and 'maxFeePerGas' in tx:
            # Type 2 transaction
            priority_fee = min(tx['maxPriorityFeePerGas'], tx['maxFeePerGas'] - base_fee)
        else:
            # Type 0 transaction (pre-EIP-1559)
            priority_fee = tx['gasPrice'] - base_fee

        if previous_fee is not None and priority_fee > previous_fee:
            return False

        previous_fee = priority_fee

    return True

# Part 2: Query values from the MerkleValidator contract on the BNB testnet
def get_contract_values(contract, admin_address, owner_address):
    """
    Queries the contract for three values and returns them.
    """
    default_admin_role = int.to_bytes(0, 32, byteorder="big")

    # Call to get the merkleRoot from the contract
    onchain_root = contract.functions.merkleRoot().call()

    # Call to check if the admin address has the default admin role
    has_role = contract.functions.hasRole(default_admin_role, admin_address).call()

    # Call to get the prime owned by the owner address
    prime = contract.functions.getPrimeByOwner(owner_address).call()

    return onchain_root, has_role, prime


# Testing function (not used in grading, feel free to modify)
if __name__ == "__main__":
    admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
    owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
    contract_file = "contract_info.json"

    eth_w3 = connect_to_eth()
    cont_w3, contract = connect_with_middleware(contract_file)

    latest_block = eth_w3.eth.get_block_number()
    london_hard_fork_block_num = 12965000
    assert latest_block > london_hard_fork_block_num, f"Error: the chain never got past the London Hard Fork"

    n = 5
    for _ in range(n):
        block_num = random.randint(1, london_hard_fork_block_num - 1)
        ordered = is_ordered_block(eth_w3, block_num)
        if ordered:
            print(f"Block {block_num} is ordered")
        else:
            print(f"Block {block_num} is not ordered")

    # Test contract values on BNB testnet
    onchain_root, has_role, prime = get_contract_values(contract, admin_address, owner_address)
    print(f"Merkle Root: {onchain_root}")
    print(f"Admin has role: {has_role}")
    print(f"Prime by owner: {prime}")
