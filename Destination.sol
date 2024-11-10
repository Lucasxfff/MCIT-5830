// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("WARDEN_ROLE");
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
    }

    /**
     * @notice Allows the creation of a new wrapped token
     * @dev Only callable by addresses with the CREATOR_ROLE
     * @param _underlying_token The address of the underlying asset on the source chain
     * @param name The name of the new wrapped token
     * @param symbol The symbol of the new wrapped token
     * @return The address of the newly created BridgeToken
     */
    function createToken(
        address _underlying_token,
        string memory name,
        string memory symbol
    ) public onlyRole(CREATOR_ROLE) returns (address) {
        require(
            underlying_tokens[_underlying_token] == address(0),
            "Token already created"
        );

        // Create a new BridgeToken for the underlying asset, assigning the contract itself as the admin
        BridgeToken newToken = new BridgeToken(
            _underlying_token,
            name,
            symbol,
            address(this)
        );
        address wrapped_token = address(newToken);

        // Update the mappings
        underlying_tokens[_underlying_token] = wrapped_token;
        wrapped_tokens[wrapped_token] = _underlying_token;
        
        // Add the wrapped token to the tokens array
        tokens.push(wrapped_token);

        emit Creation(_underlying_token, wrapped_token);

        return wrapped_token;
    }

    /**
     * @notice Mints wrapped tokens for an underlying asset on the destination chain
     * @dev Only callable by addresses with the WARDEN_ROLE
     * @param _underlying_token The address of the underlying asset on the source chain
     * @param _recipient The address to receive the newly wrapped tokens
     * @param _amount The amount of tokens to mint
     */
    function wrap(
        address _underlying_token,
        address _recipient,
        uint256 _amount
    ) public onlyRole(WARDEN_ROLE) {
        address wrapped_token = underlying_tokens[_underlying_token];
        require(wrapped_token != address(0), "Token not registered");

        // Mint wrapped tokens
        BridgeToken(wrapped_token).mint(_recipient, _amount);

        emit Wrap(_underlying_token, wrapped_token, _recipient, _amount);
    }

    /**
     * @notice Burns wrapped tokens to allow unwrapping on the source chain
     * @param _wrapped_token The address of the wrapped token being unwrapped
     * @param _recipient The address to receive the underlying tokens on the source chain
     * @param _amount The amount of tokens to burn
     */
    function unwrap(
        address _wrapped_token,
        address _recipient,
        uint256 _amount
    ) public {
        address underlying_token = wrapped_tokens[_wrapped_token];
        require(underlying_token != address(0), "Wrapped token not registered");

        // Burn tokens from sender's account
        BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);

        emit Unwrap(
            underlying_token,
            _wrapped_token,
            msg.sender,
            _recipient,
            _amount
        );
    }
}
