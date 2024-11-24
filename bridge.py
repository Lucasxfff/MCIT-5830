from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware  # Necessary for POA chains
import json
import sys
from pathlib import Path

# Constants
source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"
warden_private_key = "0x3d85dcb11d854ffe332cf0aac156f91ed0a721406aec64fc1c9f394eff60e693"


def connectTo(chain):
    """
    Connect to the specified chain and return a Web3 instance.
    """
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet
    else:
        raise ValueError(f"Invalid chain: {chain}")

    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3


def getContractInfo():
    """
    Retrieve contract information from `contract_info.json`.
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
        return contracts
    except Exception as e:
        print("Failed to read contract info:", e)
        raise e


def scanBlocks(chain):
    """
    Scan the last 5 blocks on the specified chain for relevant events.
    When a Deposit event is found on the source chain, call wrap on the destination chain.
    When an Unwrap event is found on the destination chain, call withdraw on the source chain.
    """
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    contracts = getContractInfo()
    w3 = connectTo(source_chain if chain == "source" else destination_chain)

    # Retrieve contract info based on the chain
    contract_data = contracts["source"] if chain == "source" else contracts["destination"]
    contract_address = Web3.to_checksum_address(contract_data["address"])
    abi = contract_data["abi"]
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Define event type
    event_type = "Deposit" if chain == "source" else "Unwrap"

    # Get latest block range
    latest_block = w3.eth.block_number
    from_block = latest_block - 5
    to_block = latest_block

    # Create event filter
    event_filter = contract.events[event_type].create_filter(fromBlock=from_block, toBlock=to_block)
    events = event_filter.get_all_entries()

    # Process events
    for event in events:
        args = event["args"]
        tx_hash = event["transactionHash"].hex()
        if chain == "source":  # Handle Deposit event
            token = args["token"]
            recipient = args["recipient"]
            amount = args["amount"]

            print(f"Handling Deposit event on {source_chain}")
            dest_w3 = connectTo(destination_chain)
            dest_contract_data = contracts["destination"]
            dest_contract = dest_w3.eth.contract(address=Web3.to_checksum_address(dest_contract_data["address"]),
                                                 abi=dest_contract_data["abi"])

            nonce = dest_w3.eth.get_transaction_count(Web3.to_checksum_address(warden_private_key))
            tx = dest_contract.functions.wrap(token, recipient, amount).build_transaction({
                'nonce': nonce,
                'from': dest_w3.eth.default_account,
                'gas': 3000000,
                'gasPrice': dest_w3.to_wei('10', 'gwei')
            })

            signed_tx = dest_w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
            tx_hash = dest_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Sent wrap transaction on destination chain: {tx_hash.hex()}")

        elif chain == "destination":  # Handle Unwrap event
            underlying_token = args["underlying_token"]
            recipient = args["to"]
            amount = args["amount"]

            print(f"Handling Unwrap event on {destination_chain}")
            src_w3 = connectTo(source_chain)
            src_contract_data = contracts["source"]
            src_contract = src_w3.eth.contract(address=Web3.to_checksum_address(src_contract_data["address"]),
                                               abi=src_contract_data["abi"])

            nonce = src_w3.eth.get_transaction_count(Web3.to_checksum_address(warden_private_key))
            tx = src_contract.functions.withdraw(underlying_token, recipient, amount).build_transaction({
                'nonce': nonce,
                'from': src_w3.eth.default_account,
                'gas': 3000000,
                'gasPrice': src_w3.to_wei('10', 'gwei')
            })

            signed_tx = src_w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
            tx_hash = src_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Sent withdraw transaction on source chain: {tx_hash.hex()}")


if __name__ == "__main__":
    # Example of running the scanBlocks function
    try:
        scanBlocks("source")
        scanBlocks("destination")
    except Exception as e:
        print(f"Error while scanning blocks: {e}")
