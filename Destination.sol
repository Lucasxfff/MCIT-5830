// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");

    // Mappings to track underlying and wrapped tokens
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
    }

    // Creates a new BridgeToken for the specified underlying token
    function createToken(address _underlying_token, string memory name, string memory symbol) public onlyRole(CREATOR_ROLE) returns (address) {
        require(underlying_tokens[_underlying_token] == address(0), "Token already created");

        // Deploy a new BridgeToken with the Destination contract as the admin
        BridgeToken newToken = new BridgeToken(_underlying_token, name, symbol, address(this));
        address wrapped_token = address(newToken);

        // Update mappings and tokens array
        underlying_tokens[_underlying_token] = wrapped_token;
        wrapped_tokens[wrapped_token] = _underlying_token;
        tokens.push(wrapped_token);

        // Emit the Creation event
        emit Creation(_underlying_token, wrapped_token);

        return wrapped_token;
    }

    // Mints wrapped tokens for the specified underlying asset
    function wrap(address _underlying_token, address _recipient, uint256 _amount) public onlyRole(WARDEN_ROLE) {
        // Ensure the token has been registered by checking the underlying token mapping
        address wrapped_token = underlying_tokens[_underlying_token];
        require(wrapped_token != address(0), "Token not registered");

        // Mint the specified amount to the recipient
        BridgeToken(wrapped_token).mint(_recipient, _amount);

        // Emit the Wrap event
        emit Wrap(_underlying_token, wrapped_token, _recipient, _amount);
    }

    // Burns wrapped tokens to release the underlying asset
    function unwrap(address _wrapped_token, address _recipient, uint256 _amount) public {
        // Ensure the wrapped token has a registered underlying asset
        address underlying_token = wrapped_tokens[_wrapped_token];
        require(underlying_token != address(0), "Wrapped token not registered");

        // Only the token holder can burn (unwrap) their tokens
        BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);

        // Emit the Unwrap event
        emit Unwrap(underlying_token, _wrapped_token, msg.sender, _recipient, _amount);
    }
}
