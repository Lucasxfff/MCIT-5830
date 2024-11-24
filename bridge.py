from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware  # Necessary for POA chains
import json
import pandas as pd
import sys
from pathlib import Path

# Constants
source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"
warden_private_key = "0x3d85dcb11d854ffe332cf0aac156f91ed0a721406aec64fc1c9f394eff60e693"  # Warden's private key
events_file = "bridge_events.csv"

def connectTo(chain):
    """
    Connect to the appropriate testnet (Avalanche or BNB)
    """
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet
    elif chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet
    else:
        raise ValueError("Invalid chain specified")

    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # Add middleware for POA chains
    return w3


def getContractInfo():
    """
    Load the contract_info.json file
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open("r") as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        sys.exit(1)
    return contracts


def validateEvents(chain, events):
    """
    Validate the scanned events against bridge_events.csv
    """
    df = pd.read_csv(events_file)
    if chain == "source":
        expected_events = df[df["event"] == "Deposit"]
    elif chain == "destination":
        expected_events = df[df["event"] == "Unwrap"]
    else:
        raise ValueError("Invalid chain specified")

    for event in events:
        match = expected_events[
            (expected_events["transactionHash"] == event.transactionHash.hex()) &
            (expected_events["address"] == event.address)
        ]
        if match.empty:
            print(f"Unexpected event: {event}")
        else:
            print(f"Validated event: {event}")


def scanBlocks(chain):
    """
    Scan the last 5 blocks of the source and destination chains.
    - Listen for Deposit events on the Source contract (AVAX chain)
    - Listen for Unwrap events on the Destination contract (BSC chain)
    - Trigger the appropriate cross-chain actions (wrap/unwrap)
    """
    contracts = getContractInfo()
    chain_info = contracts[source_chain if chain == "source" else destination_chain]

    w3 = connectTo(source_chain if chain == "source" else destination_chain)
    contract_address = Web3.to_checksum_address(chain_info["address"])
    contract_abi = chain_info["abi"]
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    # Scan the last 5 blocks
    latest_block = w3.eth.get_block_number()
    start_block = latest_block - 5
    print(f"Scanning {chain} chain from block {start_block} to {latest_block}")

    if chain == "source":
        # Listen for Deposit events on the Source contract
        event_filter = contract.events.Deposit.create_filter(
            fromBlock=start_block, toBlock=latest_block
        )
        events = event_filter.get_all_entries()

        validateEvents(chain, events)

        for event in events:
            token = event.args.token
            recipient = event.args.recipient
            amount = event.args.amount
            tx_hash = event.transactionHash.hex()

            print(f"Deposit Event: {token}, {recipient}, {amount}, {tx_hash}")

            # Call wrap on the Destination chain
            wrapOnDestination(token, recipient, amount)

    elif chain == "destination":
        # Listen for Unwrap events on the Destination contract
        event_filter = contract.events.Unwrap.create_filter(
            fromBlock=start_block, toBlock=latest_block
        )
        events = event_filter.get_all_entries()

        validateEvents(chain, events)

        for event in events:
            underlying_token = event.args.underlying_token
            recipient = event.args.to
            amount = event.args.amount
            tx_hash = event.transactionHash.hex()

            print(f"Unwrap Event: {underlying_token}, {recipient}, {amount}, {tx_hash}")

            # Call withdraw on the Source chain
            withdrawOnSource(underlying_token, recipient, amount)


def wrapOnDestination(token, recipient, amount):
    """
    Call the wrap function on the Destination contract
    """
    contracts = getContractInfo()
    dest_info = contracts[destination_chain]

    w3 = connectTo(destination_chain)
    contract_address = Web3.to_checksum_address(dest_info["address"])
    contract_abi = dest_info["abi"]
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    tx = contract.functions.wrap(token, recipient, amount).build_transaction({
        "chainId": w3.eth.chain_id,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(w3.eth.account.privateKeyToAccount(warden_private_key).address)
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"Wrap transaction sent: {tx_hash.hex()}")


def withdrawOnSource(token, recipient, amount):
    """
    Call the withdraw function on the Source contract
    """
    contracts = getContractInfo()
    src_info = contracts[source_chain]

    w3 = connectTo(source_chain)
    contract_address = Web3.to_checksum_address(src_info["address"])
    contract_abi = src_info
