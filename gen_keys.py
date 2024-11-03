from web3 import Web3
import eth_account
import os
from eth_account import Account
from eth_account.messages import encode_defunct

def get_keys(challenge, keyId=0, filename="eth_mnemonic.txt"):
    """
    Generate a stable private key
    challenge - byte string
    keyId (integer) - which key to use
    filename - filename to read and store mnemonics

    Each mnemonic is stored on a separate line.
    If fewer than (keyId+1) mnemonics have been generated, generate a new one and return that.
    """

    w3 = Web3()
    msg = encode_defunct(challenge)

    # Step 1: Load or generate mnemonic
    if os.path.exists(filename):
        with open(filename, "r") as f:
            mnemonics = f.read().splitlines()
    else:
        mnemonics = []

    # If mnemonic for keyId doesn't exist, create a new one and save it
    if keyId >= len(mnemonics):
        # Generate a new account and save its mnemonic
        account = Account.create()
        private_key = account.key.hex()
        mnemonics.append(private_key)
        with open(filename, "a") as f:
            f.write(private_key + "\n")
    else:
        # Retrieve the private key for the specified keyId
        private_key = mnemonics[keyId]

    # Step 2: Create account from private key
    acct = Account.from_key(private_key)
    eth_addr = acct.address

    # Step 3: Sign the message
    sig = Account.sign_message(msg, private_key=acct.key)

    # Ensure that the signature can be recovered to the correct address
    assert eth_account.Account.recover_message(msg, signature=sig.signature) == eth_addr, "Failed to sign message properly"

    # Return the signature and Ethereum address
    return sig, eth_addr

if __name__ == "__main__":
    for i in range(4):
        challenge = os.urandom(64)
        sig, addr = get_keys(challenge=challenge, keyId=i)
        print(addr)
