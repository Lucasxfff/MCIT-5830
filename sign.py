import eth_account
from eth_account import Account
from eth_account.messages import encode_defunct


def sign(m):
    # Create an Ethereum account
    account = Account.create()
    
    # Get the Ethereum address from the account
    eth_address = account.address

    # Prepare the message for signing
    message = encode_defunct(text=m)
    
    # Generate signature
    signed_message = Account.sign_message(message, private_key=account.key)

    # Ensure the signed_message is of type SignedMessage
    assert isinstance(signed_message, eth_account.datastructures.SignedMessage)

    return eth_address, signed_message
