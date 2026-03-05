"""
Hedera Consensus Service integration for DevPilot.

Posts PR review verdicts and CI incident reports as immutable messages
to a Hedera HCS topic, creating a verifiable audit trail on-chain.

Requirements:
  - HEDERA_ACCOUNT_ID: Hedera account (e.g. 0.0.12345) — get free testnet at portal.hedera.com
  - HEDERA_PRIVATE_KEY: DER-encoded private key from portal.hedera.com
  - HEDERA_TOPIC_ID: existing topic ID (optional — will create one if not set)
  - HEDERA_NETWORK: testnet (default) or mainnet
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_HEDERA_AVAILABLE = False
try:
    from hiero_sdk_python import (
        Client,
        AccountId,
        PrivateKey,
        Network,
    )
    from hiero_sdk_python.consensus.topic_create_transaction import TopicCreateTransaction
    from hiero_sdk_python.consensus.topic_message_submit_transaction import TopicMessageSubmitTransaction
    _HEDERA_AVAILABLE = True
except ImportError:
    logger.warning("hiero-sdk-python not installed — Hedera integration disabled")


def _is_configured() -> bool:
    return (
        _HEDERA_AVAILABLE
        and bool(os.environ.get("HEDERA_ACCOUNT_ID"))
        and bool(os.environ.get("HEDERA_PRIVATE_KEY"))
    )


def _get_client():
    account_id = AccountId.from_string(os.environ["HEDERA_ACCOUNT_ID"])
    private_key = PrivateKey.from_string(os.environ["HEDERA_PRIVATE_KEY"])
    network = os.environ.get("HEDERA_NETWORK", "testnet")
    if network == "mainnet":
        client = Client(Network.MAINNET)
    else:
        client = Client(Network.TESTNET)
    client.set_operator(account_id, private_key)
    return client


def _get_or_create_topic(client) -> str:
    """Return existing topic ID or create a new one."""
    topic_id = os.environ.get("HEDERA_TOPIC_ID")
    if topic_id:
        return topic_id
    logger.info("Creating new HCS topic for DevPilot audit trail")
    tx = TopicCreateTransaction()
    tx.topic_memo = "DevPilot Code Review Audit Trail"
    receipt = tx.execute(client).get_receipt(client)
    new_id = str(receipt.topic_id)
    logger.info("Created HCS topic: %s — set HEDERA_TOPIC_ID=%s to reuse", new_id, new_id)
    return new_id


def _hashscan_url(topic_id: str) -> str:
    network = os.environ.get("HEDERA_NETWORK", "testnet")
    return f"https://hashscan.io/{network}/topic/{topic_id}"


async def record_pr_review(
    repo: str,
    pr_number: int,
    verdict: str,
    summary: str,
    issues_count: int,
) -> Optional[str]:
    """
    Submit a PR review verdict to Hedera HCS.
    Returns hashscan URL for the topic, or None if Hedera is not configured.
    """
    if not _is_configured():
        return None
    try:
        client = _get_client()
        topic_id = _get_or_create_topic(client)
        payload = json.dumps({
            "type": "pr_review",
            "repo": repo,
            "pr": pr_number,
            "verdict": verdict,
            "summary": summary[:300],
            "issues_count": issues_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        tx = TopicMessageSubmitTransaction()
        tx.topic_id = topic_id
        tx.message = payload.encode()
        tx.execute(client).get_receipt(client)
        url = _hashscan_url(topic_id)
        logger.info("PR review recorded on Hedera HCS topic %s", topic_id)
        return url
    except Exception as exc:
        logger.error("Failed to record PR review on Hedera: %s", exc)
        return None


async def record_incident(
    repo: str,
    run_id: int,
    severity: str,
    root_cause: str,
) -> Optional[str]:
    """
    Submit a CI incident report to Hedera HCS.
    Returns hashscan URL for the topic, or None if Hedera is not configured.
    """
    if not _is_configured():
        return None
    try:
        client = _get_client()
        topic_id = _get_or_create_topic(client)
        payload = json.dumps({
            "type": "ci_incident",
            "repo": repo,
            "run_id": run_id,
            "severity": severity,
            "root_cause": root_cause[:300],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        tx = TopicMessageSubmitTransaction()
        tx.topic_id = topic_id
        tx.message = payload.encode()
        tx.execute(client).get_receipt(client)
        url = _hashscan_url(topic_id)
        logger.info("CI incident recorded on Hedera HCS topic %s", topic_id)
        return url
    except Exception as exc:
        logger.error("Failed to record CI incident on Hedera: %s", exc)
        return None
