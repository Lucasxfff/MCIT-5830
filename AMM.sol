// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract AMM is AccessControl {
    bytes32 public constant LP_ROLE = keccak256("LP_ROLE");
    uint256 public invariant;
    address public tokenA;
    address public tokenB;
    uint256 public feebps = 30; // Fee in basis points (0.3%)

    event Swap(address indexed _inToken, address indexed _outToken, uint256 inAmt, uint256 outAmt);
    event LiquidityProvision(address indexed _from, uint256 AQty, uint256 BQty);
    event Withdrawal(address indexed _from, address indexed recipient, uint256 AQty, uint256 BQty);

    constructor(address _tokenA, address _tokenB) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(LP_ROLE, msg.sender);

        require(_tokenA != address(0), "Token address cannot be 0");
        require(_tokenB != address(0), "Token address cannot be 0");
        require(_tokenA != _tokenB, "Tokens cannot be the same");
        tokenA = _tokenA;
        tokenB = _tokenB;
    }

    function getTokenAddress(uint256 index) public view returns (address) {
        require(index < 2, "Only two tokens");
        return index == 0 ? tokenA : tokenB;
    }

    function tradeTokens(address sellToken, uint256 sellAmount) public {
        require(invariant > 0, "Invariant must be nonzero");
        require(sellToken == tokenA || sellToken == tokenB, "Invalid token");
        require(sellAmount > 0, "Cannot trade 0");

        address buyToken = sellToken == tokenA ? tokenB : tokenA;
        ERC20 sellERC20 = ERC20(sellToken);
        ERC20 buyERC20 = ERC20(buyToken);

        uint256 sellReserve = sellERC20.balanceOf(address(this));
        uint256 buyReserve = buyERC20.balanceOf(address(this));

        uint256 feeAdjustedAmount = (sellAmount * (10000 - feebps)) / 10000;
        uint256 numerator = feeAdjustedAmount * buyReserve;
        uint256 denominator = sellReserve + feeAdjustedAmount;
        uint256 buyAmount = numerator / denominator;

        require(buyAmount > 0, "Insufficient output amount");

        require(sellERC20.transferFrom(msg.sender, address(this), sellAmount), "Transfer failed");
        require(buyERC20.transfer(msg.sender, buyAmount), "Transfer failed");

        uint256 newInvariant = sellERC20.balanceOf(address(this)) * buyERC20.balanceOf(address(this));
        require(newInvariant >= invariant, "Invariant check failed");
        invariant = newInvariant;

        emit Swap(sellToken, buyToken, sellAmount, buyAmount);
    }

    function provideLiquidity(uint256 amtA, uint256 amtB) public {
        require(amtA > 0 && amtB > 0, "Cannot provide 0 liquidity");

        ERC20 tokenAERC20 = ERC20(tokenA);
        ERC20 tokenBERC20 = ERC20(tokenB);

        require(tokenAERC20.transferFrom(msg.sender, address(this), amtA), "Transfer failed");
        require(tokenBERC20.transferFrom(msg.sender, address(this), amtB), "Transfer failed");

        invariant = tokenAERC20.balanceOf(address(this)) * tokenBERC20.balanceOf(address(this));

        emit LiquidityProvision(msg.sender, amtA, amtB);
    }

    function withdrawLiquidity(address recipient, uint256 amtA, uint256 amtB) public onlyRole(LP_ROLE) {
        require(amtA > 0 || amtB > 0, "Cannot withdraw 0");
        require(recipient != address(0), "Cannot withdraw to 0 address");

        ERC20 tokenAERC20 = ERC20(tokenA);
        ERC20 tokenBERC20 = ERC20(tokenB);

        if (amtA > 0) {
            require(tokenAERC20.transfer(recipient, amtA), "Transfer failed");
        }
        if (amtB > 0) {
            require(tokenBERC20.transfer(recipient, amtB), "Transfer failed");
        }

        invariant = tokenAERC20.balanceOf(address(this)) * tokenBERC20.balanceOf(address(this));

        emit Withdrawal(msg.sender, recipient, amtA, amtB);
    }
}
