from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware
import json
import sys
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"
warden_private_key = "0x3d85dcb11d854ffe332cf0aac156f91ed0a721406aec64fc1c9f394eff60e693"  # Replace this with your actual key

def connect_to(chain):
    """
    Connect to the blockchain network (either AVAX or BSC testnet)
    """
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError(f"Invalid chain: {chain}")

    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def get_contract_info():
    """
    Load contract information from `contract_info.json`
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        print(e)
        sys.exit(1)
    return contracts

def scan_blocks(chain):
    """
    Scan the last 5 blocks of the specified chain for events and trigger corresponding actions.
    """
    contracts = get_contract_info()
    if chain == "source":
        contract_data = contracts["source"]
        event_name = "Deposit"
        other_chain = "destination"
    elif chain == "destination":
        contract_data = contracts["destination"]
        event_name = "Unwrap"
        other_chain = "source"
    else:
        raise ValueError(f"Invalid chain: {chain}")

    w3 = connect_to(source_chain if chain == "source" else destination_chain)
    current_block = w3.eth.get_block_number()
    from_block = max(0, current_block - 5)

    contract = w3.eth.contract(address=contract_data["address"], abi=contract_data["abi"])
    event_filter = contract.events[event_name].create_filter(fromBlock=from_block, toBlock="latest")
    events = event_filter.get_all_entries()

    for event in events:
        args = event["args"]
        tx_hash = event["transactionHash"].hex()
        address = event["address"]

        if chain == "source" and event_name == "Deposit":
            token = args["token"]
            recipient = args["recipient"]
            amount = args["amount"]
            print(f"Detected Deposit: Token={token}, Recipient={recipient}, Amount={amount}, TxHash={tx_hash}")
            call_wrap(other_chain, token, recipient, amount)
        elif chain == "destination" and event_name == "Unwrap":
            underlying_token = args["underlying_token"]
            wrapped_token = args["wrapped_token"]
            frm = args["frm"]
            to = args["to"]
            amount = args["amount"]
            print(f"Detected Unwrap: UnderlyingToken={underlying_token}, WrappedToken={wrapped_token}, From={frm}, To={to}, Amount={amount}, TxHash={tx_hash}")
            call_withdraw(other_chain, underlying_token, to, amount)

def call_wrap(chain, token, recipient, amount):
    """
    Call the `wrap` function on the destination chain.
    """
    contracts = get_contract_info()
    contract_data = contracts["destination"]

    w3 = connect_to(destination_chain)
    contract = w3.eth.contract(address=contract_data["address"], abi=contract_data["abi"])

    nonce = w3.eth.get_transaction_count(w3.eth.default_account)
    tx = contract.functions.wrap(token, recipient, amount).build_transaction({
        "from": w3.eth.default_account,
        "nonce": nonce,
        "gas": 500000,
        "gasPrice": w3.to_wei("5", "gwei"),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"Called wrap on {chain}: TxHash={tx_hash.hex()}")

def call_withdraw(chain, token, recipient, amount):
    """
    Call the `withdraw` function on the source chain.
    """
    contracts = get_contract_info()
    contract_data = contracts["source"]

    w3 = connect_to(source_chain)
    contract = w3.eth.contract(address=contract_data["address"], abi=contract_data["abi"])

    nonce = w3.eth.get_transaction_count(w3.eth.default_account)
    tx = contract.functions.withdraw(token, recipient, amount).build_transaction({
        "from": w3.eth.default_account,
        "nonce": nonce,
        "gas": 500000,
        "gasPrice": w3.to_wei("5", "gwei"),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"Called withdraw on {chain}: TxHash={tx_hash.hex()}")
