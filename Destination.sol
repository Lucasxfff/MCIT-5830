// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");

    mapping(address => address) public underlying_tokens; // Map underlying token to wrapped token
    mapping(address => address) public wrapped_tokens;    // Map wrapped token to underlying token
    address[] public tokens;

    event Creation(address indexed underlying_token, address indexed wrapped_token);
    event Wrap(address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount);
    event Unwrap(address indexed underlying_token, address indexed wrapped_token, address from, address indexed to, uint256 amount);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    function createToken(address _underlying_token, string memory name, string memory symbol) 
        public 
        onlyRole(CREATOR_ROLE) 
        returns (address) 
    {
        // Ensure token is not already created
        require(underlying_tokens[_underlying_token] == address(0), "Token already created");

        // Deploy a new BridgeToken contract
        BridgeToken newToken = new BridgeToken(_underlying_token, name, symbol, address(this));
        address wrappedAddress = address(newToken);

        // Store the mapping between the underlying token and the new wrapped token
        underlying_tokens[_underlying_token] = wrappedAddress;
        wrapped_tokens[wrappedAddress] = _underlying_token;
        tokens.push(_underlying_token);

        // Emit creation event
        emit Creation(_underlying_token, wrappedAddress);

        return wrappedAddress;
    }

    function wrap(address _underlying_token, address _recipient, uint256 _amount) 
        public 
        onlyRole(WARDEN_ROLE) 
    {
        // Ensure the token has been created
        address wrappedTokenAddress = underlying_tokens[_underlying_token];
        require(wrappedTokenAddress != address(0), "Token not registered");

        // Mint the wrapped tokens for the recipient
        BridgeToken(wrappedTokenAddress).mint(_recipient, _amount);

        // Emit wrap event
        emit Wrap(_underlying_token, wrappedTokenAddress, _recipient, _amount);
    }

    function unwrap(address _wrapped_token, address _recipient, uint256 _amount) public {
        // Ensure the wrapped token is registered
        address underlyingTokenAddress = wrapped_tokens[_wrapped_token];
        require(underlyingTokenAddress != address(0), "Wrapped token not registered");

        // Burn the wrapped tokens from the caller's balance
        BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);

        // Emit unwrap event
        emit Unwrap(underlyingTokenAddress, _wrapped_token, msg.sender, _recipient, _amount);
    }
}
