"""
PCC-Tensor 3.1: Evidence Closure Certificate (ECC) & Forward-Replay Verifier.
Formal verification of source integrity, coordinate closure, unit proof,
and forward-replay semantic normalization.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .source import BoundingBox
from .evidence import EvidenceAnchor, MultiSourceProvenanceBundle, TransformationRecord
from .ctir import SourceFact
from .value import (
    TypedSemanticValue,
    ExactNumeric,
    BoundedNumeric,
    NumericRange,
    MissingValue,
    DECIMAL_CONTEXT,
    parse_exact_decimal,
)


class VerificationVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class TransformationStep:
    """A declared atomic normalization step (alias / wrapper for TransformationRecord)."""
    step_id: str
    rule_name: str
    input_text: str
    output_result: str


@dataclass(frozen=True)
class CryptoSignaturePayload:
    """Cryptographic signature authenticating the compiled fact."""
    algorithm: str = "Ed25519"
    key_id: str = "lab-root-key-01"
    payload_digest: str = ""
    signature_bytes: str = ""


@dataclass(frozen=True)
class EvidenceClosureCertificate:
    """
    ECC_fact: The formal evidence and verification certificate
    accompanying each extracted semantic fact in PCC-Tensor 3.1.
    """
    certificate_id: str
    fact_id: str
    version: str = "3.1.0"

    # 1. Source Provenance Bundle
    provenance_bundle: MultiSourceProvenanceBundle = field(default=None)  # type: ignore

    # 2. Canonical Semantic Fact Payload (Authoritative SourceFact)
    fact: SourceFact = field(default=None)  # type: ignore

    # 3. Replay Transformation Ledger
    transformation_steps: Tuple[TransformationRecord, ...] = field(default_factory=tuple)

    # 4. Cryptographic Authentication
    signature: Optional[CryptoSignaturePayload] = None

    # 5. Extraction & Interpretation Confidence Scores
    geometric_confidence: float = 1.0
    structural_confidence: float = 1.0
    semantic_confidence: float = 1.0


class FormalProofVerifier:
    """
    Independent formal verifier that checks proof obligations on Evidence Closure Certificates.
    Enforces Contracts C1, C3, C8, C10, C11, C13, and C14.
    """

    HEX_64_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
    TRUSTED_KEY_REGISTRY: Dict[str, Ed25519PublicKey] = {}

    @classmethod
    def register_trusted_key(cls, key_id: str, public_key: Ed25519PublicKey) -> None:
        """Registers a trusted Ed25519 public key in the verifier's key ring."""
        cls.TRUSTED_KEY_REGISTRY[key_id] = public_key

    @classmethod
    def clear_trusted_keys(cls) -> None:
        """Clears the trusted key ring."""
        cls.TRUSTED_KEY_REGISTRY.clear()

    @classmethod
    def sign_fact(
        cls,
        certificate_id: str,
        fact_id: str,
        canonical_display: str,
        private_key: Ed25519PrivateKey,
        key_id: str,
    ) -> CryptoSignaturePayload:
        """
        Generates an authentic Ed25519 signature payload for a fact certificate.
        """
        hasher = hashlib.sha256()
        hasher.update(certificate_id.encode("utf-8"))
        hasher.update(fact_id.encode("utf-8"))
        hasher.update(str(canonical_display).encode("utf-8"))
        digest = hasher.hexdigest()
        sig_bytes = private_key.sign(digest.encode("utf-8")).hex()
        return CryptoSignaturePayload(
            algorithm="Ed25519",
            key_id=key_id,
            payload_digest=digest,
            signature_bytes=sig_bytes,
        )

    @classmethod
    def verify_fact_certificate(cls, cert: EvidenceClosureCertificate) -> Tuple[VerificationVerdict, List[str]]:
        failures: List[str] = []

        # Obligation 1: Provenance Bundle Integrity (Contract C1 & C13)
        if cert.provenance_bundle is None or cert.provenance_bundle.value_anchor is None:
            failures.append("Obligation 1 Failed: Missing required value provenance anchor.")
        else:
            val_anchor = cert.provenance_bundle.value_anchor
            doc_hash = val_anchor.document_hash or getattr(val_anchor, "doc_sha256", "")
            if not doc_hash or not cls.HEX_64_PATTERN.match(doc_hash):
                failures.append(f"Obligation 1 Failed: Document hash is not a valid 64-character hex SHA-256: '{doc_hash}'")

            # Check bounding box validity (Contract C3)
            bbox = val_anchor.bbox
            if bbox is not None:
                if not isinstance(bbox, BoundingBox):
                    # Check legacy bbox_pts if present
                    pts = getattr(val_anchor, "bbox_pts", None)
                    if pts is None or len(pts) != 4:
                        failures.append("Obligation 1 Failed: Bounding box must be a valid BoundingBox instance.")
                else:
                    if bbox.x0 >= bbox.x1 or bbox.y0 >= bbox.y1:
                        failures.append(f"Obligation 1 Failed: Inverted bounding box coordinates ({bbox.x0}, {bbox.y0}, {bbox.x1}, {bbox.y1})")

        # Obligation 2: Forward Replay Transformation Verification (Contract C8)
        # Verifies that applying declared transformations to raw string yields the stored typed value
        raw_val = cert.provenance_bundle.value_anchor.raw_text if (cert.provenance_bundle and cert.provenance_bundle.value_anchor) else ""
        if isinstance(cert.fact.typed_value, ExactNumeric):
            expected_decimal = cert.fact.typed_value.value

            # If transformation steps are declared on certificate or fact, replay them
            tx_steps = cert.transformation_steps or cert.fact.transformations
            if tx_steps:
                from .evidence import verify_transformation_chain
                ok, err_code, err_msg = verify_transformation_chain(
                    initial_text=raw_val,
                    transformations=tx_steps,
                    expected_value=cert.fact.typed_value,
                )
                if not ok:
                    failures.append(f"Obligation 2 Failed ({err_code}): {err_msg}")
            else:
                # Direct canonical parse check
                s_clean = raw_val.strip()
                if s_clean.startswith("(") and s_clean.endswith(")"):
                    s_clean = "-" + s_clean[1:-1]
                elif s_clean.startswith("$(") and s_clean.endswith(")"):
                    s_clean = "-" + s_clean[2:-1]
                s_clean = s_clean.replace("$", "").replace(",", "").strip()
                try:
                    replayed_decimal = parse_exact_decimal(s_clean)
                    if replayed_decimal != expected_decimal:
                        failures.append(
                            f"Obligation 2 Failed (Direct Replay Mismatch): "
                            f"Replayed {replayed_decimal} != Stored {expected_decimal}"
                        )
                except Exception as e:
                    failures.append(f"Obligation 2 Failed: Parsing raised {e}")

        # Obligation 3: Temporal Coordinate Completeness (Contract C11)
        temp_coord = getattr(cert.fact.coordinates, "temporal", None) or getattr(cert.fact, "temporal", None)
        if temp_coord is None:
            failures.append("Obligation 3 Failed: Temporal coordinate is null.")

        # Obligation 4: Unit Assertion Consistency (Contract C10)
        if cert.fact.unit is None:
            failures.append("Obligation 4 Failed: Unit assertion is null.")

        # Obligation 5: Cryptographic Authenticity Verification (Contract C1)
        if cert.signature is not None:
            sig = cert.signature
            if sig.algorithm != "Ed25519":
                failures.append(f"Obligation 5 Failed: Unsupported signature algorithm '{sig.algorithm}', expected Ed25519.")

            hasher = hashlib.sha256()
            hasher.update(cert.certificate_id.encode("utf-8"))
            hasher.update(cert.fact_id.encode("utf-8"))
            canonical_disp = getattr(cert.fact, "canonical_display", None) or getattr(cert.fact, "canonical_display_value", "")
            hasher.update(str(canonical_disp).encode("utf-8"))
            computed_digest = hasher.hexdigest()

            if sig.payload_digest and sig.payload_digest != computed_digest:
                failures.append(f"Obligation 5 Failed: Cryptographic payload digest mismatch: '{sig.payload_digest}' != '{computed_digest}'")

            # Public-key authenticity verification against TRUSTED_KEY_REGISTRY
            if sig.key_id not in cls.TRUSTED_KEY_REGISTRY:
                failures.append(f"Obligation 5 Failed: Untrusted or unregistered public key ID '{sig.key_id}'.")
            else:
                pub_key = cls.TRUSTED_KEY_REGISTRY[sig.key_id]
                try:
                    if isinstance(sig.signature_bytes, str):
                        try:
                            raw_sig = bytes.fromhex(sig.signature_bytes)
                        except ValueError:
                            raw_sig = sig.signature_bytes.encode("utf-8")
                    else:
                        raw_sig = bytes(sig.signature_bytes)

                    pub_key.verify(raw_sig, computed_digest.encode("utf-8"))
                except InvalidSignature:
                    failures.append(f"Obligation 5 Failed: Ed25519 signature is invalid/forged for key '{sig.key_id}'.")
                except Exception as e:
                    failures.append(f"Obligation 5 Failed: Ed25519 cryptographic verification error: {e}")

        if not failures:
            return VerificationVerdict.PASS, []
        return VerificationVerdict.FAIL, failures
