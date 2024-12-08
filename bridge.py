from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from eth_account import Account
import os

# Constants
SOURCE_CHAIN = 'avax'
DESTINATION_CHAIN = 'bsc'
CONTRACT_INFO_FILE = "contract_info.json"
WARDEN_PRIVATE_KEY = "0x3d85dcb11d854ffe332cf0aac156f91ed0a721406aec64fc1c9f394eff60e693"
LAST_BLOCK_FILE = "last_block.txt"

def connect_to(chain):
    """
    Connect to the blockchain.
    """
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError("Invalid chain specified.")
    
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # For POA chains
    return w3

def get_contract_info(chain):
    """
    Load the contract information from the contract_info.json file.
    """
    with open(CONTRACT_INFO_FILE, 'r') as file:
        contracts = json.load(file)
    return contracts[chain]

def get_last_block(chain):
    """
    Get the last processed block for the given chain.
    """
    if os.path.exists(LAST_BLOCK_FILE):
        with open(LAST_BLOCK_FILE, 'r') as f:
            last_blocks = json.load(f)
        return last_blocks.get(chain, 0)
    return 0

def update_last_block(chain, block_number):
    """
    Update the last processed block for the given chain.
    """
    last_blocks = {}
    if os.path.exists(LAST_BLOCK_FILE):
        with open(LAST_BLOCK_FILE, 'r') as f:
            last_blocks = json.load(f)
    last_blocks[chain] = block_number
    with open(LAST_BLOCK_FILE, 'w') as f:
        json.dump(last_blocks, f)

def scan_blocks(chain):
    """
    Scan blocks for events and act upon them.
    """
    w3 = connect_to(chain)
    contract_info = get_contract_info(chain)
    contract_address = contract_info["address"]
    contract_abi = contract_info["abi"]

    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    start_block = get_last_block(chain)
    latest_block = w3.eth.block_number

    if start_block == 0:
        start_block = latest_block - 10  # Default to last 10 blocks

    print(f"Scanning blocks {start_block} to {latest_block} on {chain}...")

    if chain == SOURCE_CHAIN:
        event_filter = contract.events.Deposit.createFilter(fromBlock=start_block, toBlock="latest")
    elif chain == DESTINATION_CHAIN:
        event_filter = contract.events.Unwrap.createFilter(fromBlock=start_block, toBlock="latest")
    else:
        raise ValueError("Invalid chain specified.")

    events = event_filter.get_all_entries()

    for event in events:
        if chain == SOURCE_CHAIN:
            handle_deposit_event(event)
        elif chain == DESTINATION_CHAIN:
            handle_unwrap_event(event)

    # Update the last processed block
    update_last_block(chain, latest_block)

def handle_deposit_event(event):
    """
    Handle Deposit events from the source chain.
    """
    destination_contract_info = get_contract_info(DESTINATION_CHAIN)
    w3 = connect_to(DESTINATION_CHAIN)
    contract = w3.eth.contract(address=destination_contract_info["address"], abi=destination_contract_info["abi"])
    tx = contract.functions.wrap(
        event.args["token"],
        event.args["recipient"],
        event.args["amount"]
    ).buildTransaction({
        "chainId": w3.eth.chain_id,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.getTransactionCount(Account.from_key(WARDEN_PRIVATE_KEY).address),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=WARDEN_PRIVATE_KEY)
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        print(f"Wrap transaction confirmed: {receipt.transactionHash.hex()}")
    except Exception as e:
        print(f"Error sending wrap transaction: {e}")

def handle_unwrap_event(event):
    """
    Handle Unwrap events from the destination chain.
    """
    source_contract_info = get_contract_info(SOURCE_CHAIN)
    w3 = connect_to(SOURCE_CHAIN)
    contract = w3.eth.contract(address=source_contract_info["address"], abi=source_contract_info["abi"])
    tx = contract.functions.withdraw(
        event.args["underlying_token"],
        event.args["to"],
        event.args["amount"]
    ).buildTransaction({
        "chainId": w3.eth.chain_id,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.getTransactionCount(Account.from_key(WARDEN_PRIVATE_KEY).address),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=WARDEN_PRIVATE_KEY)
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        print(f"Withdraw transaction confirmed: {receipt.transactionHash.hex()}")
    except Exception as e:
        print(f"Error sending withdraw transaction: {e}")

if __name__ == "__main__":
    # Scan both chains for events
    scan_blocks(SOURCE_CHAIN)
    scan_blocks(DESTINATION_CHAIN)
