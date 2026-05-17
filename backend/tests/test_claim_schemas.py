"""Tests for claim schemas (Task 1.4)."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.claim import Claim, ClaimCreate, ClaimStatus


class TestClaimStatus:
    """Tests for ClaimStatus enum."""

    def test_claim_status_enum_values(self):
        """Verify all expected ClaimStatus enum values exist."""
        expected_statuses = {
            "SUPPORTED",
            "PARTIALLY_SUPPORTED",
            "CONTRADICTED",
            "UNSUPPORTED",
            "UNVERIFIABLE",
        }
        actual_statuses = {status.value for status in ClaimStatus}
        assert actual_statuses == expected_statuses

    def test_claim_status_enum_members_are_strings(self):
        """Verify ClaimStatus members are string enums."""
        assert isinstance(ClaimStatus.SUPPORTED, str)
        assert isinstance(ClaimStatus.PARTIALLY_SUPPORTED, str)
        assert isinstance(ClaimStatus.CONTRADICTED, str)
        assert isinstance(ClaimStatus.UNSUPPORTED, str)
        assert isinstance(ClaimStatus.UNVERIFIABLE, str)


class TestClaimCreate:
    """Tests for ClaimCreate schema (used before DB persistence)."""

    def test_claim_create_valid_construction(self):
        """Test creating a valid ClaimCreate object."""
        claim_data = {
            "text": "The Earth is round",
            "confidence": 0.95,
            "claim_index": 0,
            "source_span": "The Earth is round",
        }
        claim = ClaimCreate(**claim_data)
        assert claim.text == "The Earth is round"
        assert claim.confidence == 0.95
        assert claim.claim_index == 0
        assert claim.source_span == "The Earth is round"

    def test_claim_create_minimal_fields(self):
        """Test creating ClaimCreate with only required fields."""
        claim = ClaimCreate(text="Test claim", confidence=0.5)
        assert claim.text == "Test claim"
        assert claim.confidence == 0.5
        assert claim.claim_index == 0  # default
        assert claim.source_span is None  # default

    def test_claim_create_empty_text_raises(self):
        """Test that empty claim text raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClaimCreate(text="", confidence=0.5)
        assert "at least 1 character" in str(exc_info.value)

    def test_claim_create_text_too_long_raises(self):
        """Test that claim text exceeding 2000 chars raises ValidationError."""
        long_text = "x" * 2001
        with pytest.raises(ValidationError) as exc_info:
            ClaimCreate(text=long_text, confidence=0.5)
        assert "at most 2000 characters" in str(exc_info.value)

    def test_claim_create_confidence_out_of_range_raises(self):
        """Test that confidence outside 0-1 range raises ValidationError."""
        # Test too high
        with pytest.raises(ValidationError) as exc_info:
            ClaimCreate(text="Test", confidence=1.5)
        assert "less than or equal to 1" in str(exc_info.value)

        # Test too low
        with pytest.raises(ValidationError) as exc_info:
            ClaimCreate(text="Test", confidence=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_claim_create_confidence_boundaries(self):
        """Test that confidence values 0.0 and 1.0 are accepted."""
        claim_low = ClaimCreate(text="Test", confidence=0.0)
        assert claim_low.confidence == 0.0

        claim_high = ClaimCreate(text="Test", confidence=1.0)
        assert claim_high.confidence == 1.0

    def test_claim_create_negative_claim_index_raises(self):
        """Test that negative claim_index raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClaimCreate(text="Test", confidence=0.5, claim_index=-1)
        assert "greater than or equal to 0" in str(exc_info.value)


class TestClaim:
    """Tests for Claim schema (with persistence metadata and status)."""

    def test_claim_valid_construction(self):
        """Test creating a valid Claim object with all fields."""
        claim_id = uuid4()
        claim_data = {
            "id": claim_id,
            "text": "The Earth is round",
            "confidence": 0.95,
            "status": ClaimStatus.SUPPORTED,
            "claim_index": 0,
            "source_span": "The Earth is round",
        }
        claim = Claim(**claim_data)
        assert claim.id == claim_id
        assert claim.text == "The Earth is round"
        assert claim.confidence == 0.95
        assert claim.status == ClaimStatus.SUPPORTED
        assert claim.claim_index == 0
        assert claim.source_span == "The Earth is round"

    def test_claim_default_status(self):
        """Test that Claim status defaults to UNVERIFIABLE."""
        claim = Claim(
            id=uuid4(), text="Test claim", confidence=0.5, claim_index=0
        )
        assert claim.status == ClaimStatus.UNVERIFIABLE

    def test_claim_all_status_values(self):
        """Test that Claim can be created with all possible status values."""
        claim_id = uuid4()
        for status in ClaimStatus:
            claim = Claim(
                id=claim_id, text="Test", confidence=0.5, status=status, claim_index=0
            )
            assert claim.status == status

    def test_claim_confidence_validation(self):
        """Test that Claim validates confidence as inherited from ClaimCreate."""
        claim_id = uuid4()
        with pytest.raises(ValidationError):
            Claim(
                id=claim_id, text="Test", confidence=1.5, status=ClaimStatus.SUPPORTED
            )

    def test_claim_status_as_string_value(self):
        """Test that ClaimStatus can be assigned by string value."""
        claim = Claim(
            id=uuid4(),
            text="Test",
            confidence=0.5,
            status="SUPPORTED",
            claim_index=0,
        )
        assert claim.status == ClaimStatus.SUPPORTED
        assert isinstance(claim.status, ClaimStatus)


class TestClaimSerialization:
    """Tests for Claim JSON serialization and deserialization."""

    def test_claim_json_roundtrip(self):
        """Test that Claim serializes to JSON and deserializes without data loss."""
        original_claim = Claim(
            id=uuid4(),
            text="Test claim",
            confidence=0.75,
            status=ClaimStatus.PARTIALLY_SUPPORTED,
            claim_index=2,
            source_span="Original span",
        )

        # Serialize to JSON
        json_str = original_claim.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize back
        claim_dict = json.loads(json_str)
        restored_claim = Claim(**claim_dict)

        # Verify all fields match
        assert restored_claim.id == original_claim.id
        assert restored_claim.text == original_claim.text
        assert restored_claim.confidence == original_claim.confidence
        assert restored_claim.status == original_claim.status
        assert restored_claim.claim_index == original_claim.claim_index
        assert restored_claim.source_span == original_claim.source_span

    def test_claim_model_dump_to_dict(self):
        """Test that Claim.model_dump() produces correct dictionary."""
        claim_id = uuid4()
        claim = Claim(
            id=claim_id,
            text="Test",
            confidence=0.8,
            status=ClaimStatus.CONTRADICTED,
            claim_index=1,
        )
        claim_dict = claim.model_dump()

        assert claim_dict["id"] == claim_id
        assert claim_dict["text"] == "Test"
        assert claim_dict["confidence"] == 0.8
        assert claim_dict["status"] == "CONTRADICTED"
        assert claim_dict["claim_index"] == 1

    def test_claim_model_dump_includes_none_values(self):
        """Test that model_dump includes None values for optional fields."""
        claim = Claim(
            id=uuid4(), text="Test", confidence=0.5, claim_index=0, source_span=None
        )
        claim_dict = claim.model_dump()
        assert "source_span" in claim_dict
        assert claim_dict["source_span"] is None

    def test_claim_json_with_uuid_serialization(self):
        """Test that UUID fields are properly serialized in JSON."""
        claim_id = uuid4()
        claim = Claim(
            id=claim_id, text="Test", confidence=0.5, claim_index=0
        )
        json_str = claim.model_dump_json()
        claim_dict = json.loads(json_str)

        # UUID should be serialized as string
        assert isinstance(claim_dict["id"], str)
        # And deserializable back to UUID
        restored_claim = Claim(**claim_dict)
        assert restored_claim.id == claim_id

    def test_claim_status_serialized_as_string(self):
        """Test that ClaimStatus is serialized as string value."""
        claim = Claim(
            id=uuid4(),
            text="Test",
            confidence=0.5,
            status=ClaimStatus.PARTIALLY_SUPPORTED,
            claim_index=0,
        )
        json_str = claim.model_dump_json()
        claim_dict = json.loads(json_str)

        assert isinstance(claim_dict["status"], str)
        assert claim_dict["status"] == "PARTIALLY_SUPPORTED"


class TestClaimEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_claim_create_confidence_decimal_values(self):
        """Test that confidence accepts various decimal values."""
        for confidence in [0.0, 0.333, 0.5, 0.666, 0.999, 1.0]:
            claim = ClaimCreate(text="Test", confidence=confidence)
            assert claim.confidence == confidence

    def test_claim_large_claim_index(self):
        """Test that large claim_index values are accepted."""
        claim = Claim(
            id=uuid4(), text="Test", confidence=0.5, claim_index=9999, status=ClaimStatus.SUPPORTED
        )
        assert claim.claim_index == 9999

    def test_claim_text_with_special_characters(self):
        """Test that claim text can contain special characters."""
        special_text = "What is the meaning of life, the universe, & everything? 🤔"
        claim = ClaimCreate(text=special_text, confidence=0.5)
        assert claim.text == special_text

    def test_claim_text_with_newlines(self):
        """Test that claim text can contain newlines."""
        multiline_text = "Line 1\nLine 2\nLine 3"
        claim = ClaimCreate(text=multiline_text, confidence=0.5)
        assert claim.text == multiline_text

    def test_claim_source_span_empty_string(self):
        """Test that empty source_span is allowed (different from None)."""
        claim = ClaimCreate(text="Test", confidence=0.5, source_span="")
        assert claim.source_span == ""
