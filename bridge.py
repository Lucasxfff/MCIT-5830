from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware  # Necessary for POA chains
import json
import sys
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"
warden_private_key = "your_private_key_here"

def connectTo(chain):
    """
    Connect to a blockchain based on the provided chain name ('avax' or 'bsc').
    """
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet
    elif chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet
    else:
        raise ValueError(f"Unsupported chain: {chain}")

    w3 = Web3(Web3.HTTPProvider(api_url))
    # Inject the POA compatibility middleware to the innermost layer
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def getContractInfo(*args):
    """
    Load the contract_info.json file into a dictionary.
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open("r") as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        print(e)
        sys.exit(1)
    return contracts

def scanBlocks(chain):
    """
    Scan the last 5 blocks of the source and destination chains for specific events.
    """
    w3 = connectTo(chain)
    contract_data = getContractInfo()[chain]
    contract = w3.eth.contract(address=Web3.to_checksum_address(contract_data["address"]),
                               abi=contract_data["abi"])
    
    latest_block = w3.eth.get_block_number()
    start_block = max(latest_block - 5, 0)
    end_block = latest_block

    print(f"Scanning blocks {start_block} to {end_block} on {chain}")

    # Event-specific logic
    if chain == 'source':
        event_filter = contract.events.Deposit.create_filter(fromBlock=start_block, toBlock=end_block)
        events = event_filter.get_all_entries()
        for event in events:
            processDepositEvent(w3, event)
    elif chain == 'destination':
        event_filter = contract.events.Unwrap.create_filter(fromBlock=start_block, toBlock=end_block)
        events = event_filter.get_all_entries()
        for event in events:
            processUnwrapEvent(w3, event)

def processDepositEvent(w3, event):
    """
    Process a Deposit event from the source chain.
    """
    contract_data = getContractInfo()['destination']
    contract = w3.eth.contract(address=Web3.to_checksum_address(contract_data["address"]),
                               abi=contract_data["abi"])

    transaction = contract.functions.wrap(
        event.args['token'],
        event.args['recipient'],
        event.args['amount']
    ).build_transaction({
        "from": w3.eth.default_account,
        "nonce": w3.eth.get_transaction_count(w3.eth.default_account)
    })

    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=warden_private_key)
    w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"Processed Deposit event: {event.args}")

def processUnwrapEvent(w3, event):
    """
    Process an Unwrap event from the destination chain.
    """
    contract_data = getContractInfo()['source']
    contract = w3.eth.contract(address=Web3.to_checksum_address(contract_data["address"]),
                               abi=contract_data["abi"])

    transaction = contract.functions.withdraw(
        event.args['underlying_token'],
        event.args['to'],
        event.args['amount']
    ).build_transaction({
        "from": w3.eth.default_account,
        "nonce": w3.eth.get_transaction_count(w3.eth.default_account)
    })

    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=warden_private_key)
    w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"Processed Unwrap event: {event.args}")

if __name__ == "__main__":
    """
    Main execution: listens for events and processes them.
    """
    for chain in ['source', 'destination']:
        scanBlocks(chain)
