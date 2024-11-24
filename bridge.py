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

# Warden's private key
warden_private_key = "0x3d85dcb11d854ffe332cf0aac156f91ed0a721406aec64fc1c9f394eff60e693"

def connectTo(chain):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet

    if chain in ['avax', 'bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # Inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def getContractInfo():
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

    return contracts

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

    w3 = connectTo(source_chain if chain == 'source' else destination_chain)
    contract_info = getContractInfo()

    contract_details = contract_info['source'] if chain == 'source' else contract_info['destination']
    contract_address = Web3.to_checksum_address(contract_details['address'])
    contract_abi = contract_details['abi']

    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    latest_block = w3.eth.get_block_number()
    start_block = max(latest_block - 5, 0)

    if chain == 'source':
        event_filter = contract.events.Deposit.create_filter(fromBlock=start_block, toBlock=latest_block)
        events = event_filter.get_all_entries()

        for event in events:
            token = event.args['token']
            recipient = event.args['recipient']
            amount = event.args['amount']

            destination_w3 = connectTo(destination_chain)
            destination_contract_details = contract_info['destination']
            destination_contract_address = Web3.to_checksum_address(destination_contract_details['address'])
            destination_contract_abi = destination_contract_details['abi']
            destination_contract = destination_w3.eth.contract(address=destination_contract_address, abi=destination_contract_abi)

            tx = destination_contract.functions.wrap(token, recipient, amount).build_transaction({
                'from': w3.eth.default_account,
                'nonce': destination_w3.eth.get_transaction_count(w3.eth.default_account),
                'gas': 300000,
                'gasPrice': destination_w3.to_wei('20', 'gwei')
            })

            signed_tx = destination_w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
            tx_hash = destination_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Wrap transaction sent: {tx_hash.hex()}")

    elif chain == 'destination':
        event_filter = contract.events.Unwrap.create_filter(fromBlock=start_block, toBlock=latest_block)
        events = event_filter.get_all_entries()

        for event in events:
            underlying_token = event.args['underlying_token']
            recipient = event.args['to']
            amount = event.args['amount']

            source_w3 = connectTo(source_chain)
            source_contract_details = contract_info['source']
            source_contract_address = Web3.to_checksum_address(source_contract_details['address'])
            source_contract_abi = source_contract_details['abi']
            source_contract = source_w3.eth.contract(address=source_contract_address, abi=source_contract_abi)

            tx = source_contract.functions.withdraw(underlying_token, recipient, amount).build_transaction({
                'from': w3.eth.default_account,
                'nonce': source_w3.eth.get_transaction_count(w3.eth.default_account),
                'gas': 300000,
                'gasPrice': source_w3.to_wei('20', 'gwei')
            })

            signed_tx = source_w3.eth.account.sign_transaction(tx, private_key=warden_private_key)
            tx_hash = source_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Withdraw transaction sent: {tx_hash.hex()}")
