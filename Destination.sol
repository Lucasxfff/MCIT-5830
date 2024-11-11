// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
    
    // Mappings for tracking wrapped and underlying tokens
    mapping(address => address) public underlying_tokens; // Maps underlying token to wrapped token
    mapping(address => address) public wrapped_tokens;    // Maps wrapped token to underlying token
    address[] public tokens;

    // Events to signal actions
    event Creation(address indexed underlying_token, address indexed wrapped_token);
    event Wrap(address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount);
    event Unwrap(address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount);

    constructor(address admin) {
        // Grant roles to the admin
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    // Create a new wrapped token for an underlying asset
    function createToken(address _underlying_token, string memory name, string memory symbol) public onlyRole(CREATOR_ROLE) returns (address) {
        require(underlying_tokens[_underlying_token] == address(0), "Token already created");

        // Deploy a new BridgeToken contract
        BridgeToken newToken = new BridgeToken(_underlying_token, name, symbol, address(this));
        address wrapped_token = address(newToken);

        // Update mappings to track the new wrapped token
        underlying_tokens[_underlying_token] = wrapped_token;
        wrapped_tokens[wrapped_token] = _underlying_token;
        tokens.push(wrapped_token);

        // Emit creation event
        emit Creation(_underlying_token, wrapped_token);

        return wrapped_token;
    }

    // Mint wrapped tokens for the underlying asset
    function wrap(address _underlying_token, address _recipient, uint256 _amount) public onlyRole(WARDEN_ROLE) {
        address wrapped_token = underlying_tokens[_underlying_token];
        require(wrapped_token != address(0), "Token not registered");

        // Mint tokens to the recipient
        BridgeToken(wrapped_token).mint(_recipient, _amount);

        // Emit wrap event
        emit Wrap(_underlying_token, wrapped_token, _recipient, _amount);
    }

    // Burn wrapped tokens for unwrapping
    function unwrap(address _wrapped_token, address _recipient, uint256 _amount) public {
        address underlying_token = wrapped_tokens[_wrapped_token];
        require(underlying_token != address(0), "Wrapped token not registered");

        // Burn tokens from the sender's account
        BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);

        // Emit unwrap event
        emit Unwrap(underlying_token, _wrapped_token, msg.sender, _recipient, _amount);
    }
}
