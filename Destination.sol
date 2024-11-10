// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";
import "forge-std/console.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
    
    mapping(address => address) public underlying_tokens; // Maps underlying token to wrapped token
    mapping(address => address) public wrapped_tokens;    // Maps wrapped token to underlying token
    address[] public tokens;

    event Creation(address indexed underlying_token, address indexed wrapped_token);
    event Wrap(address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount);
    event Unwrap(address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
        console.log("Admin role granted to:", admin);
    }

    // Allows the creation of a new wrapped token
    function createToken(address _underlying_token, string memory name, string memory symbol) public onlyRole(CREATOR_ROLE) returns (address) {
        require(underlying_tokens[_underlying_token] == address(0), "Token already created");

        console.log("Creating wrapped token for underlying asset:", _underlying_token);
        
        BridgeToken newToken = new BridgeToken(_underlying_token, name, symbol, address(this));
        address wrapped_token = address(newToken);

        underlying_tokens[_underlying_token] = wrapped_token;
        wrapped_tokens[wrapped_token] = _underlying_token;
        tokens.push(wrapped_token);

        emit Creation(_underlying_token, wrapped_token);

        console.log("Wrapped token created at address:", wrapped_token);

        return wrapped_token;
    }

    // Mints wrapped tokens for an underlying asset
    function wrap(address _underlying_token, address _recipient, uint256 _amount) public onlyRole(WARDEN_ROLE) {
        address wrapped_token = underlying_tokens[_underlying_token];
        require(wrapped_token != address(0), "Token not registered");

        console.log("Minting tokens to recipient:", _recipient);
        console.log("Underlying token:", _underlying_token, "Wrapped token:", wrapped_token, "Amount:", _amount);

        BridgeToken(wrapped_token).mint(_recipient, _amount);

        emit Wrap(_underlying_token, wrapped_token, _recipient, _amount);
    }

    // Burns wrapped tokens for unwrapping
    function unwrap(address _wrapped_token, address _recipient, uint256 _amount) public {
        address underlying_token = wrapped_tokens[_wrapped_token];
        require(underlying_token != address(0), "Wrapped token not registered");

        console.log("Burning tokens from sender:", msg.sender);
        console.log("Wrapped token:", _wrapped_token, "Recipient:", _recipient, "Amount:", _amount);

        BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);

        emit Unwrap(underlying_token, _wrapped_token, msg.sender, _recipient, _amount);
    }
}
