from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware  # Necessary for POA chains
import json
import sys
from pathlib import Path
from eth_account import Account

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"
warden_private_key = "0x3d85dcb11d854ffe332cf0aac156f91ed0a721406aec64fc1c9f394eff60e693"

def connectTo(chain):
    """
    Connect to the blockchain
    """
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet

    if chain in ['avax', 'bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return w3
    else:
        raise ValueError(f"Unsupported chain: {chain}")

def getContractInfo(chain):
    """
    Load the contract_info file into a dictionary
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        print("Please contact your instructor")
        print(e)
        sys.exit(1)

    return contracts[chain]

def scanBlocks(chain):
    """
    Scan the last 5 blocks of the source and destination chains
    Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
    When Deposit events are found on the source chain, call the 'wrap' function on the destination chain
    When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """
    if chain not in ['source', 'destination']:
        raise ValueError(f"Invalid chain: {chain}")

    w3 = connectTo("avax" if chain == "source" else "bsc")
    contract_info = getContractInfo(chain)
    contract_address = contract_info["address"]
    contract_abi = contract_info["abi"]

    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    latest_block = w3.eth.block_number
    start_block = latest_block - 5  # Scan the last 5 blocks

    if chain == "source":
        event_filter = contract.events.Deposit.createFilter(fromBlock=start_block, toBlock="latest")
    elif chain == "destination":
        event_filter = contract.events.Unwrap.createFilter(fromBlock=start_block, toBlock="latest")
    
    events = event_filter.get_all_entries()
    if not events:
        print(f"No events detected on {chain} chain.")
    else:
        for event in events:
            print(f"Detected Event: {event}")
            if chain == "source":
                handleDepositEvent(event)
            elif chain == "destination":
                handleUnwrapEvent(event)

def handleDepositEvent(event):
    """
    Handle Deposit events from the source chain
    """
    print("Handling Deposit Event...")
    try:
        destination_contract_info = getContractInfo("destination")
        w3 = connectTo(destination_chain)
        contract = w3.eth.contract(address=destination_contract_info["address"], abi=destination_contract_info["abi"])
        
        tx = contract.functions.wrap(
            event.args["token"],
            event.args["recipient"],
            event.args["amount"]
        ).buildTransaction({
            "chainId": w3.eth.chain_id,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.getTransactionCount(Account.from_key(warden_private_key).address),
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Wrap transaction sent: {tx_hash.hex()}")
    except Exception as e:
        print(f"Error in handleDepositEvent: {e}")

def handleUnwrapEvent(event):
    """
    Handle Unwrap events from the destination chain
    """
    print("Handling Unwrap Event...")
    try:
        source_contract_info = getContractInfo("source")
        w3 = connectTo(source_chain)
        contract = w3.eth.contract(address=source_contract_info["address"], abi=source_contract_info["abi"])

        tx = contract.functions.withdraw(
            event.args["underlying_token"],
            event.args["to"],
            event.args["amount"]
        ).buildTransaction({
            "chainId": w3.eth.chain_id,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.getTransactionCount(Account.from_key(warden_private_key).address),
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Withdraw transaction sent: {tx_hash.hex()}")
    except Exception as e:
        print(f"Error in handleUnwrapEvent: {e}")

if __name__ == "__main__":
    """
    Entry point for the bridge.py script
    """
    if len(sys.argv) != 2:
        print("Usage: python bridge.py <chain>")
        print("chain - either 'source' or 'destination'")
        sys.exit(1)

    chain = sys.argv[1]
    scanBlocks(chain)
