#!/bin/python3
import logging
from lib import Contract, State
from lib.Util import getPrivateKey, getChecksumAddr


log = logging.getLogger(__name__)


# This class initializes an Orchestrator object
class Orchestrator:
    def __init__(self, obj):
        # Orch details
        self.source_address = obj._source_address
        # Get private key
        self.source_private_key = getPrivateKey(obj._source_key, obj._source_password)
        # If the password was set via file or environment var but failed to decrypt, exit
        if self.source_private_key == "":
            log.error("Fatal error: Unable to decrypt keystore file. Exiting...")
            exit(1)
        self.source_checksum_address = getChecksumAddr(obj._source_address)
        # Set target adresses
        self.target_address = obj._target_address
        self.target_checksum_address = getChecksumAddr(obj._target_address)


# For each configured keystore, create a Orchestrator object
if len(State.KEYSTORE_CONFIGS) != 1:
    log.error("Only 1 Keystore Config is currently supported. Exiting...")
    exit(1)


State.orchestrator = Orchestrator(State.KEYSTORE_CONFIGS[0])


def withdraw_fees():
    # Main logic
    log.info("### Withdrawing Fees ###")
    pending_fees = Contract.pendingFees()
    if pending_fees < State.ETH_THRESHOLD:
        log.info("{0} has {1:.4f} ETH in pending fees < threshold of {2:.4f} ETH".format(State.orchestrator.source_address, pending_fees, State.ETH_THRESHOLD))
    else:
        log.info("{0} has {1:.4f} in ETH pending fees > threshold of {2:.4f} ETH, withdrawing fees...".format(State.orchestrator.source_address, pending_fees, State.ETH_THRESHOLD))
        Contract.doWithdrawFees()


def fund_deposit():
    log.info("### Funding Deposit ###")
    balance = Contract.getEthBalance()
    # Transfer ETH to Receiver Gateway's Deposit if threshold is reached
    if balance < State.ETH_THRESHOLD:
        log.info("{0} has {1:.4f} ETH in their wallet < threshold of {2:.4f} ETH".format(State.orchestrator.source_address, balance, State.ETH_THRESHOLD))
    elif State.ETH_MINVAL > balance:
        log.info("Cannot send ETH, as the minimum value {0:.4f} ETH to leave behind is larger than the balance {1:.4f} ETH".format(State.ETH_MINVAL, balance))
    else:
        log.info("{0} has {1:.4f} in ETH pending fees > threshold of {2:.4f} ETH, sending some to {3}...".format(State.orchestrator.source_address, balance, State.ETH_THRESHOLD, State.orchestrator.target_address))
        Contract.doFundDeposit(float(balance) - State.ETH_MINVAL)


withdraw_fees()
fund_deposit()
