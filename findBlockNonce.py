#!/bin/python
import hashlib
import os
import random

def mine_block(k, prev_hash, rand_lines):
    """
        k - Number of trailing zeros in the binary representation (integer)
        prev_hash - the hash of the previous block (bytes)
        rand_lines - a set of "transactions," i.e., data to be included in this block (list of strings)

        Complete this function to find a nonce such that 
        sha256( prev_hash + rand_lines + nonce )
        has k trailing zeros in its *binary* representation
    """
    if not isinstance(k, int) or k < 0:
        print("mine_block expects positive integer")
        return b'\x00'

    nonce = 0  # Start nonce from 0

    while True:
        # Convert nonce to bytes
        nonce_bytes = str(nonce).encode('utf-8')
        
        # Combine prev_hash, each transaction, and nonce into a single byte string
        block_data = prev_hash
        for line in rand_lines:
            block_data += line.encode('utf-8')
        block_data += nonce_bytes
        
        # Compute the SHA256 hash
        block_hash = hashlib.sha256(block_data).digest()
        
        # Convert hash to binary and check if it has k trailing zeros
        binary_hash = bin(int.from_bytes(block_hash, byteorder='big'))
        
        if binary_hash[-k:] == '0' * k:
            return nonce_bytes  # Return nonce in bytes format
        
        # Increment nonce and try again
        nonce += 1

def get_random_lines(filename, quantity):
    """
    This is a helper function to get the quantity of lines ("transactions")
    as a list from the filename given. 
    Do not modify this function
    """
    lines = []
    with open(filename, 'r') as f:
        for line in f:
            lines.append(line.strip())

    random_lines = []
    for x in range(quantity):
        random_lines.append(lines[random.randint(0, quantity - 1)])
    return random_lines

if __name__ == '__main__':
    # This code will be helpful for your testing
    filename = "bitcoin_text.txt"
    num_lines = 10  # The number of "transactions" included in the block

    # The "difficulty" level. For our blocks this is the number of Least Significant Bits
    # that are 0s. For example, if diff = 5 then the last 5 bits of a valid block hash would be zeros
    # The grader will not exceed 20 bits of "difficulty" because larger values take to long
    diff = 5

    rand_lines = get_random_lines(filename, num_lines)
    prev_hash = hashlib.sha256(b"previous block hash").digest()  # Sample previous hash
    nonce = mine_block(diff, prev_hash, rand_lines)
    print(f"Nonce found: {nonce}")
