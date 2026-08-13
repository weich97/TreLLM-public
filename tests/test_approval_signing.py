"""Adversarial tests for authenticated approval signatures.

The claim under test is bounded: the approval pipeline is forgery-resistant
against an adversary who can rewrite the artifact store but does not hold the
approver's private key. Each test names the attack it rules out.
"""

from __future__ import annotations

import json

import pytest

from tradearena.tools.approval_signing import (
    SIGNATURE_FIELD,
    ApprovalSigningError,
    canonical_signing_payload,
    generate_approver_keypair,
    public_key_hex,
    sign_approval_artifact,
    verify_approval_artifact_file,
    verify_approval_signature,
)

ARTIFACT = {
    "approval_id": "sess-001-approval-001",
    "approval_status": "approved",
    "approved_by": "operator-a",
    "approved_at": "2026-08-09T00:00:00Z",
    "expires_at": "2026-08-10T00:00:00Z",
    "request_artifact_hash": "sha256:" + "ab" * 32,
    "account_mode": "live",
    "max_notional": 10_000.0,
    "max_quantity": 100.0,
    "allowed_symbols": ["SYN", "ALT"],
    "allowed_order_types": ["limit"],
    "approval_reason": "reviewed weekly handoff",
}


@pytest.fixture()
def approver_key(tmp_path):
    key_path = tmp_path / "keys" / "approver.ed25519"
    public_hex = generate_approver_keypair(key_path)
    return key_path, public_hex


def test_signed_approval_verifies_against_the_trusted_key(approver_key):
    key_path, public_hex = approver_key
    signed = sign_approval_artifact(ARTIFACT, key_path)
    assert verify_approval_signature(signed, [public_hex]) == []


def test_unsigned_approval_is_rejected(approver_key):
    _, public_hex = approver_key
    errors = verify_approval_signature(ARTIFACT, [public_hex])
    assert errors == ["approval artifact carries no signature block"]


@pytest.mark.parametrize(
    "field, tampered",
    [
        ("approved_by", "attacker"),
        ("request_artifact_hash", "sha256:" + "cd" * 32),
        ("max_notional", 10_000_000.0),
        ("expires_at", "2099-01-01T00:00:00Z"),
        ("allowed_symbols", ["SYN", "ALT", "EVIL"]),
        ("approval_status", "approved_with_waiver"),
    ],
)
def test_field_tampering_invalidates_the_signature(approver_key, field, tampered):
    """An adversary who rewrites any authority-bearing field is caught."""

    key_path, public_hex = approver_key
    signed = sign_approval_artifact(ARTIFACT, key_path)
    signed[field] = tampered
    errors = verify_approval_signature(signed, [public_hex])
    assert errors == ["approval signature does not verify over the signed fields"]


def test_resigning_with_an_untrusted_key_is_rejected(tmp_path, approver_key):
    """The core attack: rewrite the artifact and re-sign it with your own key.

    A verifier that trusted the key embedded in the artifact would accept this.
    """

    _, trusted_public = approver_key
    attacker_key = tmp_path / "attacker.ed25519"
    attacker_public = generate_approver_keypair(attacker_key)
    assert attacker_public != trusted_public

    forged = dict(ARTIFACT)
    forged["approved_by"] = "attacker"
    forged["max_notional"] = 10_000_000.0
    forged = sign_approval_artifact(forged, attacker_key)

    # Internally consistent: it verifies under the key it names.
    assert verify_approval_signature(forged, [attacker_public]) == []
    # But not against the key the deployment actually trusts.
    assert verify_approval_signature(forged, [trusted_public]) == [
        "approval was signed by a key that is not in the trusted approver set"
    ]


def test_stripping_a_field_does_not_change_the_signed_meaning(approver_key):
    """Dropping a field must not silently shrink what the signature covers."""

    key_path, public_hex = approver_key
    signed = sign_approval_artifact(ARTIFACT, key_path)
    del signed["max_notional"]
    assert verify_approval_signature(signed, [public_hex]) == [
        "approval signature does not verify over the signed fields"
    ]


def test_narrowing_the_declared_field_set_is_rejected(approver_key):
    """An adversary must not be able to claim the signature covers less."""

    key_path, public_hex = approver_key
    signed = sign_approval_artifact(ARTIFACT, key_path)
    signed[SIGNATURE_FIELD]["signed_fields"] = ["approval_id"]
    assert verify_approval_signature(signed, [public_hex]) == [
        "approval signature does not cover the required field set"
    ]


def test_empty_trust_set_never_verifies(approver_key):
    key_path, _ = approver_key
    signed = sign_approval_artifact(ARTIFACT, key_path)
    assert verify_approval_signature(signed, []) == [
        "no trusted approver public keys were supplied"
    ]


def test_canonical_payload_is_order_independent(approver_key):
    """Key order in the JSON object must not change the signed bytes."""

    reordered = dict(reversed(list(ARTIFACT.items())))
    assert canonical_signing_payload(ARTIFACT) == canonical_signing_payload(reordered)


def test_public_key_hex_matches_generated_key(approver_key):
    key_path, public_hex = approver_key
    assert public_key_hex(key_path) == public_hex


def test_generate_refuses_to_overwrite(approver_key):
    key_path, _ = approver_key
    with pytest.raises(ApprovalSigningError):
        generate_approver_keypair(key_path)


def test_file_verifier_round_trip(tmp_path, approver_key):
    key_path, public_hex = approver_key
    signed = sign_approval_artifact(ARTIFACT, key_path)
    path = tmp_path / "broker_approval_artifact.json"
    path.write_text(json.dumps(signed), encoding="utf-8")
    assert verify_approval_artifact_file(path, [public_hex]) == []

    tampered = dict(signed)
    tampered["approved_by"] = "attacker"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    assert verify_approval_artifact_file(path, [public_hex]) != []
