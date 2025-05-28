# Any functions which requires reading/writing smart contracts gets dumped here
# Also connects to the RPC provider and holds accessors to the smart contracts

import web3  # Currency conversions
import sys
import json
import logging
from lib import State


log = logging.getLogger(__name__)


BONDING_CONTRACT_ADDR = '0x35Bcf3c30594191d53231E4FF333E8A770453e40'
TICKET_BROKER_CONTRACT_ADDR = '0xa8bB618B1520E284046F3dFc448851A1Ff26e41B'


# Define contracts

def getABI(path):
    """
    Returns a dict with ABI data

    :param str path: absolute/relative path to an ABI file
    """
    try:
        with open(path) as f:
            info_json = json.load(f)
            return info_json["abi"]
    except Exception:
        log.exception("Fatal error: Unable to extract ABI data")
        sys.exit(1)


abi_bonding_manager = getABI(State.SIPHON_ROOT + "/contracts/BondingManager.json")
abi_ticket_broker = getABI(State.SIPHON_ROOT + "/contracts/TicketBroker.json")

# connect to L2 rpc provider
provider = web3.HTTPProvider(State.L2_RPC_PROVIDER)
w3 = web3.Web3(provider)
assert w3.is_connected()

# prepare contracts
bonding_contract = w3.eth.contract(address=BONDING_CONTRACT_ADDR, abi=abi_bonding_manager)
ticket_broker_contract = w3.eth.contract(address=TICKET_BROKER_CONTRACT_ADDR, abi=abi_ticket_broker)


# Orchestrator ETH logic

def pendingFees() -> float:
    try:
        pending_wei = bonding_contract.functions.pendingFees(State.orchestrator.source_checksum_address, 99999).call()
        return web3.Web3.from_wei(pending_wei, 'ether')
    except Exception:
        log.warning("Unable to get pending fees", exc_info=True)
        return 0.0


def doWithdrawFees():
    try:
        # We take a little bit off due to floating point inaccuracies causing tx's to fail
        transfer_amount = web3.Web3.to_wei(float(State.orchestrator.balance_ETH_pending) - 0.00001, 'ether')
        receiver_address = State.orchestrator.source_checksum_address
        log.info("Withdrawing %s WEI to %s", transfer_amount, State.orchestrator.source_address)
        # Build transaction info
        transaction_obj = bonding_contract.functions.withdrawFees(receiver_address, transfer_amount).build_transaction(
            {
                "from": State.orchestrator.source_checksum_address,
                'maxFeePerGas': 2000000000,
                'maxPriorityFeePerGas': 1000000000,
                "nonce": w3.eth.get_transaction_count(State.orchestrator.source_checksum_address)
            }
        )
        # Sign and initiate transaction
        signed_transaction = w3.eth.account.sign_transaction(transaction_obj, State.orchestrator.source_private_key)
        transaction_hash = w3.eth.send_raw_transaction(signed_transaction.raw_transaction)
        log.info("Initiated transaction with hash %s", transaction_hash.hex())
        # Wait for transaction to be confirmed
        w3.eth.wait_for_transaction_receipt(transaction_hash)
        log.info('Withdraw fees success.')
    except Exception:
        log.exception("Unable to withdraw fees")


def getEthBalance() -> float:
    try:
        balance_wei = w3.eth.get_balance(State.orchestrator.source_checksum_address)
        balance_ETH = web3.Web3.from_wei(balance_wei, 'ether')
        return balance_ETH
    except Exception:
        log.exception("Unable to get ETH balance")


def doFundDeposit(amount):
    try:
        receiver_address = State.orchestrator.target_checksum_address
        log.info("Sending deposit %s WEI directly to receiver's deposit %s", amount, State.orchestrator.target_address)
        amount_wei = web3.Web3.to_wei(amount, 'ether')
        # Build transaction info
        transaction_obj = ticket_broker_contract.functions.fundDepositAndReserveFor(receiver_address, amount_wei, 0).build_transaction(
            {
                "from": State.orchestrator.source_checksum_address,
                'maxFeePerGas': 2000000000,
                'maxPriorityFeePerGas': 1000000000,
                'value': amount_wei,
                "nonce": w3.eth.get_transaction_count(State.orchestrator.source_checksum_address),
                'gas': 300000,
                'chainId': 54321
            }
        )
        # Sign and initiate transaction
        signed_transaction = w3.eth.account.sign_transaction(transaction_obj, State.orchestrator.source_private_key)
        transaction_hash = w3.eth.send_raw_transaction(signed_transaction.raw_transaction)
        log.info("Initiated transaction with hash %s", transaction_hash.hex())
        # Wait for transaction to be confirmed
        w3.eth.wait_for_transaction_receipt(transaction_hash)
        log.info("Fund deposit success.")
    except Exception:
        log.exception("Unable to fund deposit")
