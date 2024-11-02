import eth_account
from web3 import Web3
from eth_account.messages import encode_defunct


def sign(m):
    w3 = Web3()
    # Create an Ethereum account
    account = Account.create()
    
    # Get the Ethereum address and private key
    eth_address = account.address
    private_key = account.key

    # Prepare the message for signing
    message = encode_defunct(text=m)
    
    # Sign the message using the account's private key
    signed_message = Account.sign_message(message, private_key)

    assert isinstance(signed_message, eth_account.datastructures.SignedMessage)

    return eth_address, signed_message
