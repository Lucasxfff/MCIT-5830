import eth_account
import random
import string
import json
from pathlib import Path
from web3 import Web3
from web3.middleware import geth_poa_middleware  # Necessary for POA chains

def merkle_assignment():
    """
    Generate Merkle proof, claim a prime, and provide a signed challenge.
    """
    # Generate the list of primes as integers
    num_of_primes = 8192
    primes = generate_primes(num_of_primes)

    # Create a version of the list of primes in bytes32 format
    leaves = convert_leaves(primes)

    # Build a Merkle tree using the bytes32 leaves as the Merkle tree's leaves
    tree = build_merkle(leaves)

    # Select a random leaf and create a proof for that leaf
    random_leaf_index = random.randint(1, num_of_primes - 1)  # Random unclaimed prime
    proof = prove_merkle(tree, random_leaf_index)

    # Generate a challenge and sign it to verify ownership
    challenge = ''.join(random.choice(string.ascii_letters) for i in range(32))
    addr, sig = sign_challenge(challenge)

    if sign_challenge_verify(challenge, addr, sig):
        tx_hash = send_signed_msg(proof, leaves[random_leaf_index])
        print(f"Transaction hash: {tx_hash}")

def generate_primes(num_primes):
    primes = []
    candidate = 2
    while len(primes) < num_primes:
        if all(candidate % p != 0 for p in primes):
            primes.append(candidate)
        candidate += 1
    return primes

def convert_leaves(primes_list):
    return [int.to_bytes(p, (p.bit_length() + 7) // 8, 'big').rjust(32, b'\x00') for p in primes_list]

def build_merkle(leaves):
    tree = [leaves]
    while len(tree[-1]) > 1:
        layer = []
        for i in range(0, len(tree[-1]), 2):
            a = tree[-1][i]
            b = tree[-1][i + 1] if i + 1 < len(tree[-1]) else a
            layer.append(hash_pair(a, b))
        tree.append(layer)
    return tree

def prove_merkle(merkle_tree, random_index):
    proof = []
    layer_index = random_index
    for layer in merkle_tree[:-1]:
        sibling_index = layer_index ^ 1
        sibling_hash = layer[sibling_index] if sibling_index < len(layer) else layer[layer_index]
        proof.append(sibling_hash)
        layer_index //= 2
    return proof

def sign_challenge(challenge):
    acct = get_account()
    eth_encoded_msg = eth_account.messages.encode_defunct(text=challenge)
    eth_sig_obj = acct.sign_message(eth_encoded_msg)
    return acct.address, eth_sig_obj.signature.hex()

def send_signed_msg(proof, random_leaf):
    chain = 'bsc'
    acct = get_account()
    w3 = connect_to(chain)
    address, abi = get_contract_info(chain)
    contract = w3.eth.contract(address=address, abi=abi)

    nonce = w3.eth.get_transaction_count(acct.address)
    gas_price = w3.eth.gas_price

    txn = contract.functions.submit(proof, random_leaf).build_transaction({
        'chainId': 97,  # BSC testnet chain ID
        'gas': 300000,
        'gasPrice': gas_price,
        'nonce': nonce
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=acct.key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash.hex()

# Helper functions that do not need to be modified
def connect_to(chain):
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError("Invalid chain specified")
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def get_account():
    cur_dir = Path(__file__).parent.absolute()
    with open(cur_dir.joinpath('sk.txt'), 'r') as f:
        sk = f.readline().strip()
    return eth_account.Account.from_key(sk)

def get_contract_info(chain):
    cur_dir = Path(__file__).parent.absolute()
    with open(cur_dir.joinpath("contract_info.json"), "r") as f:
        d = json.load(f)[chain]
    return d['address'], d['abi']

def sign_challenge_verify(challenge, addr, sig):
    eth_encoded_msg = eth_account.messages.encode_defunct(text=challenge)
    recovered_addr = eth_account.Account.recover_message(eth_encoded_msg, signature=sig)
    success = recovered_addr == addr
    print(f"Success: {success}, Address: {addr}, Signature: {sig}")
    return success

def hash_pair(a, b):
    return Web3.solidity_keccak(['bytes32', 'bytes32'], sorted([a, b]))

if __name__ == "__main__":
    merkle_assignment()
