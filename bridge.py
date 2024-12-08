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
warden_private_key = "0x3d85dcb11d854ffe332cf0aac156f91ed0a721406aec64fc1c9f394eff60e693"


def connectTo(chain):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet

    if chain in ['avax', 'bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3


def getContractInfo(chain):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
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
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    w3 = connectTo(chain)
    contract_data = getContractInfo(chain)
    contract_address = contract_data["address"]
    contract_abi = contract_data["abi"]
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    latest_block = w3.eth.block_number
    start_block = max(0, latest_block - 5)  # Scan the last 5 blocks
    print(f"Scanning blocks {start_block} to {latest_block} on {chain}")

    if chain == 'source':
        event_filter = contract.events.Deposit.create_filter(fromBlock=start_block, toBlock="latest")
    elif chain == 'destination':
        event_filter = contract.events.Unwrap.create_filter(fromBlock=start_block, toBlock="latest")
    else:
        return

    events = event_filter.get_all_entries()
    for event in events:
        if chain == "source":
            handleDepositEvent(event)
        elif chain == "destination":
            handleUnwrapEvent(event)


def handleDepositEvent(event):
    """
    Handle Deposit events from the source chain
    """
    print("Handling Deposit Event...")
    destination_contract_data = getContractInfo("destination")
    w3 = connectTo("bsc")
    contract = w3.eth.contract(address=destination_contract_data["address"], abi=destination_contract_data["abi"])

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
    print(f"Wrap transaction sent on destination chain: {tx_hash.hex()}")


def handleUnwrapEvent(event):
    """
    Handle Unwrap events from the destination chain
    """
    print("Handling Unwrap Event...")
    source_contract_data = getContractInfo("source")
    w3 = connectTo("avax")
    contract = w3.eth.contract(address=source_contract_data["address"], abi=source_contract_data["abi"])

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
    print(f"Withdraw transaction sent on source chain: {tx_hash.hex()}")


if __name__ == "__main__":
    try:
        print("Scanning source chain for Deposit events...")
        scanBlocks("source")
        print("Scanning destination chain for Unwrap events...")
        scanBlocks("destination")
    except Exception as e:
        print(f"Error while running bridge: {e}")
