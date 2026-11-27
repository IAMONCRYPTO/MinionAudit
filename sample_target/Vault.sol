// Intentionally vulnerable demo. Do not deploy.
pragma solidity ^0.4.24;
contract Vault {
    address public owner;
    function withdraw(address to) public {
        require(tx.origin == owner);
        to.call.value(address(this).balance)("");
    }
    function setOwner(address next) public { owner = next; }
}
