"""Add payer_policies table with seed data for top 5 payers x 6 procedures

Revision ID: 011
Revises: 010
Create Date: 2026-04-01
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_DATA = [
    # UHC
    {"payer": "UHC", "procedure": "Total Knee Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "X-ray showing bone-on-bone or KL Grade III-IV", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "UHCprovider.com"}, "source_url": "https://www.uhcprovider.com/en/prior-auth/prior-auth-overview.html"},
    {"payer": "UHC", "procedure": "Total Hip Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "X-ray showing severe joint space narrowing", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "UHCprovider.com"}, "source_url": "https://www.uhcprovider.com/en/prior-auth/prior-auth-overview.html"},
    {"payer": "UHC", "procedure": "Lumbar Fusion", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT >= 6 weeks", "NSAIDs", "Epidural injection"], "imaging_required": "MRI showing instability, stenosis, or spondylolisthesis", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "UHCprovider.com"}, "source_url": "https://www.uhcprovider.com/en/prior-auth/prior-auth-overview.html"},
    {"payer": "UHC", "procedure": "Cervical Fusion", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "NSAIDs", "Cervical epidural"], "imaging_required": "MRI showing cord compression or radiculopathy", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "UHCprovider.com"}, "source_url": "https://www.uhcprovider.com/en/prior-auth/prior-auth-overview.html"},
    {"payer": "UHC", "procedure": "Spinal Cord Stimulator", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "Medications", "Injections", "Psychological eval"], "imaging_required": "MRI or CT confirming pathology", "imaging_max_age_months": 12, "functional_impairment_required": True, "trial_required": True, "submission_portal": "UHCprovider.com"}, "source_url": "https://www.uhcprovider.com/en/prior-auth/prior-auth-overview.html"},
    {"payer": "UHC", "procedure": "Rotator Cuff Repair", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Subacromial injection"], "imaging_required": "MRI showing full-thickness tear", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "UHCprovider.com"}, "source_url": "https://www.uhcprovider.com/en/prior-auth/prior-auth-overview.html"},
    # Aetna
    {"payer": "Aetna", "procedure": "Total Knee Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT >= 6 weeks", "NSAIDs >= 3 months", "Weight loss if BMI > 40"], "imaging_required": "X-ray showing KL Grade III-IV", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Availity"}, "source_url": "https://www.aetna.com/cpb/medical/data/700_799/0743.html"},
    {"payer": "Aetna", "procedure": "Total Hip Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "X-ray showing severe OA changes", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Availity"}, "source_url": "https://www.aetna.com/cpb/medical/data/700_799/0743.html"},
    {"payer": "Aetna", "procedure": "Lumbar Fusion", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT >= 6 weeks", "NSAIDs", "Epidural x2"], "imaging_required": "MRI within 6 months", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Availity"}, "source_url": "https://www.aetna.com/cpb/medical/data/200_299/0743.html"},
    {"payer": "Aetna", "procedure": "Cervical Fusion", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "MRI showing disc herniation or myelopathy", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Availity"}, "source_url": "https://www.aetna.com/cpb/medical/data/200_299/0743.html"},
    {"payer": "Aetna", "procedure": "Spinal Cord Stimulator", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "Medications", "Injections", "Psych eval required"], "imaging_required": "MRI/CT", "imaging_max_age_months": 12, "functional_impairment_required": True, "trial_required": True, "trial_success_threshold": "50% pain reduction", "submission_portal": "Availity"}, "source_url": "https://www.aetna.com/cpb/medical/data/100_199/0150.html"},
    {"payer": "Aetna", "procedure": "Rotator Cuff Repair", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT >= 6 weeks", "NSAIDs", "Injection"], "imaging_required": "MRI showing full-thickness tear", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Availity"}, "source_url": "https://www.aetna.com/cpb/medical/data/700_799/0743.html"},
    # BCBS
    {"payer": "BCBS", "procedure": "Total Knee Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT >= 6 weeks", "NSAIDs", "Injection"], "imaging_required": "Weight-bearing X-ray", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Varies by state plan"}, "source_url": "https://www.bcbs.com/"},
    {"payer": "BCBS", "procedure": "Total Hip Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "X-ray showing OA changes", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Varies by state plan"}, "source_url": "https://www.bcbs.com/"},
    {"payer": "BCBS", "procedure": "Lumbar Fusion", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Epidural"], "imaging_required": "MRI", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Varies by state plan"}, "source_url": "https://www.bcbs.com/"},
    {"payer": "BCBS", "procedure": "Cervical Fusion", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs"], "imaging_required": "MRI showing disc or cord pathology", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Varies by state plan"}, "source_url": "https://www.bcbs.com/"},
    {"payer": "BCBS", "procedure": "Spinal Cord Stimulator", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "Medications", "Injections", "Psych eval"], "imaging_required": "MRI/CT", "imaging_max_age_months": 12, "functional_impairment_required": True, "trial_required": True, "submission_portal": "Varies by state plan"}, "source_url": "https://www.bcbs.com/"},
    {"payer": "BCBS", "procedure": "Rotator Cuff Repair", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "MRI", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Varies by state plan"}, "source_url": "https://www.bcbs.com/"},
    # Cigna
    {"payer": "Cigna", "procedure": "Total Knee Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT >= 6 weeks", "NSAIDs", "Injection"], "imaging_required": "X-ray showing KL Grade III-IV", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "eviCore"}, "source_url": "https://www.evicore.com/"},
    {"payer": "Cigna", "procedure": "Total Hip Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "X-ray", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "eviCore"}, "source_url": "https://www.evicore.com/"},
    {"payer": "Cigna", "procedure": "Lumbar Fusion", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT >= 6 weeks", "NSAIDs", "Epidural"], "imaging_required": "MRI within 6 months", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "eviCore"}, "source_url": "https://www.evicore.com/"},
    {"payer": "Cigna", "procedure": "Cervical Fusion", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "MRI", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "eviCore"}, "source_url": "https://www.evicore.com/"},
    {"payer": "Cigna", "procedure": "Spinal Cord Stimulator", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "Medications", "Injections", "Psych eval"], "imaging_required": "MRI/CT", "imaging_max_age_months": 12, "functional_impairment_required": True, "trial_required": True, "submission_portal": "eviCore"}, "source_url": "https://www.evicore.com/"},
    {"payer": "Cigna", "procedure": "Rotator Cuff Repair", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT >= 6 weeks", "NSAIDs"], "imaging_required": "MRI showing tear", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "eviCore"}, "source_url": "https://www.evicore.com/"},
    # Humana
    {"payer": "Humana", "procedure": "Total Knee Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Bracing"], "imaging_required": "X-ray", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Humana provider portal"}, "source_url": "https://www.humana.com/provider"},
    {"payer": "Humana", "procedure": "Total Hip Replacement", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs"], "imaging_required": "X-ray showing OA", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Humana provider portal"}, "source_url": "https://www.humana.com/provider"},
    {"payer": "Humana", "procedure": "Lumbar Fusion", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs", "Injection"], "imaging_required": "MRI", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Humana provider portal"}, "source_url": "https://www.humana.com/provider"},
    {"payer": "Humana", "procedure": "Cervical Fusion", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs"], "imaging_required": "MRI", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Humana provider portal"}, "source_url": "https://www.humana.com/provider"},
    {"payer": "Humana", "procedure": "Spinal Cord Stimulator", "criteria": {"conservative_treatment_min_months": 6, "required_modalities": ["PT", "Medications", "Injections", "Psych eval"], "imaging_required": "MRI/CT", "imaging_max_age_months": 12, "functional_impairment_required": True, "trial_required": True, "submission_portal": "Humana provider portal or Cohere Health"}, "source_url": "https://www.humana.com/provider"},
    {"payer": "Humana", "procedure": "Rotator Cuff Repair", "criteria": {"conservative_treatment_min_months": 3, "required_modalities": ["PT", "NSAIDs"], "imaging_required": "MRI", "imaging_max_age_months": 6, "functional_impairment_required": True, "submission_portal": "Humana provider portal"}, "source_url": "https://www.humana.com/provider"},
]


def upgrade() -> None:
    op.create_table(
        "payer_policies",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("payer", sa.String(50), nullable=False),
        sa.Column("procedure", sa.String(100), nullable=False),
        sa.Column("criteria", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("source_hash", sa.String(64)),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("effective_date", sa.DateTime(timezone=True)),
        sa.Column("verified_date", sa.DateTime(timezone=True)),
        sa.Column("changelog", sa.Text()),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_payer_policies_payer", "payer_policies", ["payer"])
    op.create_index("ix_payer_policies_procedure", "payer_policies", ["procedure"])
    op.create_index("ix_payer_policies_payer_procedure", "payer_policies", ["payer", "procedure"])

    # Seed data
    for record in SEED_DATA:
        criteria_json = json.dumps(record["criteria"]).replace("'", "''")
        op.execute(
            f"INSERT INTO payer_policies (payer, procedure, criteria, source_url, verified_date, status) "
            f"VALUES ('{record['payer']}', '{record['procedure']}', "
            f"'{criteria_json}'::jsonb, '{record.get('source_url', '')}', now(), 'active')"
        )


def downgrade() -> None:
    op.drop_index("ix_payer_policies_payer_procedure")
    op.drop_index("ix_payer_policies_procedure")
    op.drop_index("ix_payer_policies_payer")
    op.drop_table("payer_policies")
