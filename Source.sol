// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract Source is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
	mapping( address => bool) public approved;
	address[] public tokens;

	event Deposit( address indexed token, address indexed recipient, uint256 amount );
	event Withdrawal( address indexed token, address indexed recipient, uint256 amount );
	event Registration( address indexed token );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

	/*
		The deposit function allows users to deposit registered ERC20 tokens.
		The contract will pull the tokens using transferFrom after confirming the token is registered.
	*/
	function deposit(address _token, address _recipient, uint256 _amount ) public {
		// Check if the token is registered
		require(approved[_token], "Token not approved for bridging");
		
		// Transfer tokens from sender to this contract
		ERC20(_token).transferFrom(msg.sender, address(this), _amount);

		// Emit Deposit event
		emit Deposit(_token, _recipient, _amount);
	}

	/*
		The withdraw function allows the bridge to release tokens to a recipient.
		Only accounts with WARDEN_ROLE can execute this function.
	*/
	function withdraw(address _token, address _recipient, uint256 _amount ) onlyRole(WARDEN_ROLE) public {
		// Transfer the tokens to the recipient
		ERC20(_token).transfer(_recipient, _amount);

		// Emit Withdrawal event
		emit Withdrawal(_token, _recipient, _amount);
	}

	/*
		The registerToken function registers a new token for bridging.
		Only ADMIN_ROLE can call this function to add tokens to the approved list.
	*/
	function registerToken(address _token) onlyRole(ADMIN_ROLE) public {
		// Check that the token isn't already registered
		require(!approved[_token], "Token already registered");

		// Register the token
		approved[_token] = true;
		tokens.push(_token);

		// Emit Registration event
		emit Registration(_token);
	}
}
