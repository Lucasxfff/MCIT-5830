from web3 import Web3
import eth_account
import os
from eth_account import Account
from eth_account.messages import encode_defunct

def get_keys(challenge, keyId=0, filename="eth_mnemonic.txt"):
    """
    Generate or retrieve a stable private key.
    challenge - byte string
    keyId (integer) - which key to use
    filename - filename to read and store private keys

    Each private key is stored on a separate line.
    If fewer than (keyId+1) keys have been generated, generate a new one and save it.
    """

    w3 = Web3()
    msg = encode_defunct(challenge)

    # Step 1: Load existing private keys or create the file if it doesn’t exist
    if os.path.exists(filename):
        with open(filename, "r") as f:
            keys = f.read().splitlines()
    else:
        keys = []

    # Step 2: Check if private key for keyId exists; otherwise, generate and save a new one
    if keyId >= len(keys):
        # Generate a new account and save its private key
        new_account = Account.create()
        private_key = new_account.key.hex()
        keys.append(private_key)
        with open(filename, "a") as f:
            f.write(private_key + "\n")
    else:
        # Retrieve the private key for the specified keyId
        private_key = keys[keyId]

    # Step 3: Create account from private key
    acct = Account.from_key(private_key)
    eth_addr = acct.address

    # Step 4: Sign the message
    sig = acct.sign_message(msg)

    # Ensure that the signature can be recovered to the correct address
    assert eth_account.Account.recover_message(msg, signature=sig.signature) == eth_addr, "Failed to sign message properly"

    # Return the signature and Ethereum address
    return sig, eth_addr

if __name__ == "__main__":
    for i in range(4):
        challenge = os.urandom(64)
        sig, addr = get_keys(challenge=challenge, keyId=i)
        print(addr)
