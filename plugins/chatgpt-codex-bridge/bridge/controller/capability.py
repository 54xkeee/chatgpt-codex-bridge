# Generic Signed Capability Codec for Executor Controller
# Refactored and generalized from Codex MCP Guard v2 capability security layer.

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

CAPABILITY_KEY_BYTES = 32
CAPABILITY_RAW_ID_MAX_BYTES = 128
CAPABILITY_PREFIX = "cgb2"


class CapabilityError(Exception):
    """Base exception for capability validation failures."""
    pass


class CapabilityConfigurationError(CapabilityError):
    pass


class CapabilityProtocolError(CapabilityError):
    pass


def capability_context(workspace, sandbox="danger-full-access", approval_policy="never", runtime_id=""):
    canonical = os.path.realpath(str(workspace)) if os.path.exists(str(workspace)) else str(workspace)
    payload = {
        "approvalPolicy": approval_policy,
        "sandbox": sandbox,
        "workspace": canonical,
    }
    if runtime_id:
        payload["runtimeId"] = runtime_id
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class CapabilityCodec:
    AUDIENCES = frozenset({
        "session",
        "session-request",
        "job",
        "thread",
        "project",
        "repository",
        "projects-cursor",
        "repositories-cursor",
        "threads-cursor",
        "items-cursor",
        "jobs-cursor",
        "models-cursor",
    })

    def __init__(self, key_path, context=""):
        self.key_path = Path(key_path)
        if not self.key_path.is_absolute() or self.key_path.is_symlink():
            raise CapabilityConfigurationError("Invalid capability key path")
        if not isinstance(context, str):
            raise CapabilityConfigurationError("Context must be a string")
        context_bytes = context.encode("utf-8")
        self.context = self._encode_part(hashlib.sha256(context_bytes).digest())
        self.key = self._load_or_create_key()

    def _load_or_create_key(self):
        try:
            descriptor = os.open(
                str(self.key_path),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            descriptor = None
        except OSError as error:
            raise CapabilityConfigurationError("Cannot open key path") from error
        if descriptor is not None:
            key = secrets.token_bytes(CAPABILITY_KEY_BYTES)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(key)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as error:
                raise CapabilityConfigurationError("Cannot write key") from error
        try:
            if self.key_path.is_symlink() or not self.key_path.is_file():
                raise CapabilityConfigurationError("Key path invalid")
            if os.name != "nt" and os.path.realpath(str(self.key_path)) != str(self.key_path):
                raise CapabilityConfigurationError("Symlinked key rejected")
            if os.name != "nt":
                os.chmod(self.key_path, 0o600)
            key = self.key_path.read_bytes()
        except OSError as error:
            raise CapabilityConfigurationError("Cannot read key") from error
        if len(key) != CAPABILITY_KEY_BYTES:
            raise CapabilityConfigurationError("Key length mismatch")
        return key

    @staticmethod
    def _encode_part(raw):
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode_part(encoded):
        if not encoded or not re.fullmatch(r"[A-Za-z0-9_-]+", encoded):
            raise CapabilityProtocolError("invalid capability")
        padding = "=" * (-len(encoded) % 4)
        try:
            value = base64.b64decode(
                encoded + padding,
                altchars=b"-_",
                validate=True,
            )
        except (ValueError, TypeError) as error:
            raise CapabilityProtocolError("invalid capability") from error
        if CapabilityCodec._encode_part(value) != encoded:
            raise CapabilityProtocolError("invalid capability")
        return value

    def encode(self, audience, raw_identifier):
        if audience not in self.AUDIENCES or not isinstance(raw_identifier, str):
            raise CapabilityProtocolError("invalid capability input")
        raw = raw_identifier.encode("utf-8")
        if not raw or len(raw) > CAPABILITY_RAW_ID_MAX_BYTES:
            raise CapabilityProtocolError("invalid capability input")
        encoded = self._encode_part(raw)
        signed = f"{CAPABILITY_PREFIX}.{audience}.{self.context}.{encoded}"
        signature = hmac.new(self.key, signed.encode("ascii"), hashlib.sha256).digest()
        return f"{signed}.{self._encode_part(signature)}"

    def decode(self, audience, capability):
        if not isinstance(capability, str):
            raise CapabilityProtocolError("invalid capability")
        parts = capability.split(".")
        if len(parts) != 5:
            raise CapabilityProtocolError("invalid capability")
        prefix, found_audience, context, encoded, signature = parts
        if prefix != CAPABILITY_PREFIX or found_audience != audience or context != self.context:
            raise CapabilityProtocolError("invalid capability")
        signed = f"{prefix}.{found_audience}.{context}.{encoded}"
        expected = hmac.new(self.key, signed.encode("ascii"), hashlib.sha256).digest()
        provided = self._decode_part(signature)
        if not hmac.compare_digest(expected, provided):
            raise CapabilityProtocolError("invalid capability")
        return self._decode_part(encoded).decode("utf-8", errors="strict")
