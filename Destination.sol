// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");

    mapping(address => address) public underlying_tokens;
    mapping(address => address) public wrapped_tokens;
    address[] public tokens;

    event Creation(
        address indexed underlying_token,
        address indexed wrapped_token
    );
    event Wrap(
        address indexed underlying_token,
        address indexed wrapped_token,
        address indexed to,
        uint256 amount
    );
    event Unwrap(
        address indexed underlying_token,
        address indexed wrapped_token,
        address frm,
        address indexed to,
        uint256 amount
    );

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    function createToken(
        address _underlying_token,
        string memory name,
        string memory symbol
    ) public onlyRole(CREATOR_ROLE) returns (address) {
        require(
            wrapped_tokens[_underlying_token] == address(0),
            "Wrapped token already exists for this underlying token"
        );

        BridgeToken newToken = new BridgeToken(
            _underlying_token,
            name,
            symbol,
            msg.sender
        );

        address wrappedTokenAddress = address(newToken);
        wrapped_tokens[_underlying_token] = wrappedTokenAddress;
        underlying_tokens[wrappedTokenAddress] = _underlying_token;
        tokens.push(wrappedTokenAddress);

        emit Creation(_underlying_token, wrappedTokenAddress);
        return wrappedTokenAddress;
    }

    function wrap(
        address _underlying_token,
        address _recipient,
        uint256 _amount
    ) public onlyRole(WARDEN_ROLE) {
        address wrappedTokenAddress = wrapped_tokens[_underlying_token];
        require(
            wrappedTokenAddress != address(0),
            "No wrapped token exists for this underlying token"
        );

        BridgeToken wrappedToken = BridgeToken(wrappedTokenAddress);
        wrappedToken.mint(_recipient, _amount);

        emit Wrap(_underlying_token, wrappedTokenAddress, _recipient, _amount);
    }

    function unwrap(
        address _wrapped_token,
        address _recipient,
        uint256 _amount
    ) public {
        address underlyingTokenAddress = underlying_tokens[_wrapped_token];
        require(
            underlyingTokenAddress != address(0),
            "No underlying token exists for this wrapped token"
        );

        BridgeToken wrappedToken = BridgeToken(_wrapped_token);
        wrappedToken.burnFrom(msg.sender, _amount);

        emit Unwrap(
            underlyingTokenAddress,
            _wrapped_token,
            msg.sender,
            _recipient,
            _amount
        );
    }
}