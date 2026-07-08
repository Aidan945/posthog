from posthog.test.base import BaseTest
from unittest.mock import MagicMock

from posthog.models.enrichment_signup_snapshot import EnrichmentSignupSnapshot

from ee.billing.salesforce_enrichment.signup_snapshot import (
    SNAPSHOT_EVENT_NAME,
    SignupEnrichmentSnapshot,
    capture_signup_enrichment_snapshot,
)


class TestSignupEnrichmentSnapshot(BaseTest):
    def test_to_event_properties_suffixes_keys_and_drops_none(self):
        snapshot = SignupEnrichmentSnapshot(
            company_type="startup",
            headcount=42,
            industry="software",
            icp_score=80,
        )

        properties = snapshot.to_event_properties()

        assert properties == {
            "company_type_at_signup": "startup",
            "headcount_at_signup": 42,
            "industry_at_signup": "software",
            "icp_score_at_signup": 80,
        }
        assert "country_at_signup" not in properties

    def test_emits_person_scoped_event_when_snapshot_lands(self):
        pha_client = MagicMock()
        snapshot = SignupEnrichmentSnapshot(company_type="startup", headcount=42)

        emitted = capture_signup_enrichment_snapshot(
            pha_client,
            organization_id=str(self.organization.id),
            distinct_id="user-distinct-id",
            snapshot=snapshot,
        )

        assert emitted is True
        pha_client.capture.assert_called_once_with(
            distinct_id="user-distinct-id",
            event=SNAPSHOT_EVENT_NAME,
            properties={"company_type_at_signup": "startup", "headcount_at_signup": 42},
            groups={"organization": str(self.organization.id)},
        )
        assert EnrichmentSignupSnapshot.objects.filter(organization_id=self.organization.id).count() == 1

    def test_written_once_second_call_does_not_re_emit(self):
        pha_client = MagicMock()
        snapshot = SignupEnrichmentSnapshot(company_type="startup")

        first = capture_signup_enrichment_snapshot(
            pha_client,
            organization_id=str(self.organization.id),
            distinct_id="user-distinct-id",
            snapshot=snapshot,
        )
        second = capture_signup_enrichment_snapshot(
            pha_client,
            organization_id=str(self.organization.id),
            distinct_id="user-distinct-id",
            snapshot=SignupEnrichmentSnapshot(company_type="enterprise"),
        )

        assert first is True
        assert second is False
        pha_client.capture.assert_called_once()
        assert EnrichmentSignupSnapshot.objects.filter(organization_id=self.organization.id).count() == 1

    def test_does_not_emit_when_guard_row_preexists(self):
        pha_client = MagicMock()
        EnrichmentSignupSnapshot.objects.create(organization_id=self.organization.id)

        emitted = capture_signup_enrichment_snapshot(
            pha_client,
            organization_id=str(self.organization.id),
            distinct_id="user-distinct-id",
            snapshot=SignupEnrichmentSnapshot(company_type="startup"),
        )

        assert emitted is False
        pha_client.capture.assert_not_called()

    def test_icp_score_version_propagated_when_present(self):
        pha_client = MagicMock()
        snapshot = SignupEnrichmentSnapshot(icp_score=90, icp_score_version="2026-07-01")

        capture_signup_enrichment_snapshot(
            pha_client,
            organization_id=str(self.organization.id),
            distinct_id="user-distinct-id",
            snapshot=snapshot,
        )

        _, kwargs = pha_client.capture.call_args
        assert kwargs["properties"]["icp_score_at_signup"] == 90
        assert kwargs["properties"]["icp_score_version_at_signup"] == "2026-07-01"

    def test_icp_score_version_omitted_when_absent(self):
        pha_client = MagicMock()
        snapshot = SignupEnrichmentSnapshot(icp_score=90)

        capture_signup_enrichment_snapshot(
            pha_client,
            organization_id=str(self.organization.id),
            distinct_id="user-distinct-id",
            snapshot=snapshot,
        )

        _, kwargs = pha_client.capture.call_args
        assert "icp_score_version_at_signup" not in kwargs["properties"]
