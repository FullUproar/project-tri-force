"""Email notification service using Resend.

All notifications are opt-in — only sent if Resend API key is configured.
Never includes PHI in email content.
"""

import resend

from app.config import settings
from app.core.logging import logger


def _is_configured() -> bool:
    return bool(settings.resend_api_key)


def _send(to: str, subject: str, html: str) -> None:
    """Send an email via Resend. Fails silently (logs error, never blocks)."""
    if not _is_configured():
        return

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent: %s -> %s", subject, to)
    except Exception as e:
        logger.error("Failed to send email (%s): %s", subject, str(e))


def notify_job_completed(to: str, org_name: str, case_short_id: str | None = None) -> None:
    """Notify that an extraction job completed successfully."""
    case_ref = f" (Case {case_short_id})" if case_short_id else ""
    _send(
        to=to,
        subject=f"Extraction Complete{case_ref} — CortaLoom",
        html=f"""
        <h2>Extraction Complete</h2>
        <p>A prior authorization extraction has completed successfully for <strong>{org_name}</strong>{case_ref}.</p>
        <p>Log in to <a href="https://cortaloom.ai">CortaLoom</a> to review the results and generate a payer narrative.</p>
        <p style="color: #888; font-size: 12px;">CortaLoom AI — Automated Prior Authorization</p>
        """,
    )


def notify_job_failed(to: str, org_name: str, error_summary: str = "Processing error") -> None:
    """Notify that an extraction job failed."""
    _send(
        to=to,
        subject=f"Extraction Failed — CortaLoom",
        html=f"""
        <h2>Extraction Failed</h2>
        <p>A prior authorization extraction failed for <strong>{org_name}</strong>.</p>
        <p><strong>Reason:</strong> {error_summary}</p>
        <p>You can retry the job from your <a href="https://cortaloom.ai">CortaLoom dashboard</a>.</p>
        <p style="color: #888; font-size: 12px;">CortaLoom AI — Automated Prior Authorization</p>
        """,
    )


def notify_budget_warning(to: str, org_name: str, usage_pct: float, count: int, limit: int) -> None:
    """Notify at 80% or 100% usage threshold."""
    threshold = "80%" if usage_pct < 100 else "100%"
    _send(
        to=to,
        subject=f"Usage Alert: {threshold} of extraction limit — CortaLoom",
        html=f"""
        <h2>Usage Alert: {threshold}</h2>
        <p><strong>{org_name}</strong> has used <strong>{count}</strong> of <strong>{limit}</strong> included extractions this billing cycle.</p>
        {"<p>Overages will be billed at $2.50 per extraction.</p>" if usage_pct >= 100 else "<p>You're approaching your included extraction limit.</p>"}
        <p>Manage your plan at <a href="https://cortaloom.ai/billing">CortaLoom Billing</a>.</p>
        <p style="color: #888; font-size: 12px;">CortaLoom AI — Automated Prior Authorization</p>
        """,
    )


def notify_denial(to: str, org_name: str, case_short_id: str | None = None, denial_reason: str = "") -> None:
    """Notify that a case was marked as denied."""
    case_ref = f" (Case {case_short_id})" if case_short_id else ""
    reason_block = f"<p><strong>Denial reason:</strong> {denial_reason[:200]}</p>" if denial_reason else ""
    _send(
        to=to,
        subject=f"Prior Auth Denied{case_ref} — CortaLoom",
        html=f"""
        <h2>Prior Authorization Denied</h2>
        <p>A prior authorization was denied for <strong>{org_name}</strong>{case_ref}.</p>
        {reason_block}
        <p>You can generate an appeal letter from your <a href="https://cortaloom.ai">CortaLoom dashboard</a>.</p>
        <p style="color: #888; font-size: 12px;">CortaLoom AI — Automated Prior Authorization</p>
        """,
    )


def notify_subscription_change(to: str, org_name: str, status: str, tier: str | None = None) -> None:
    """Notify about subscription status changes."""
    tier_info = f" ({tier.capitalize()} plan)" if tier else ""
    _send(
        to=to,
        subject=f"Subscription {status.capitalize()}{tier_info} — CortaLoom",
        html=f"""
        <h2>Subscription Update</h2>
        <p>The subscription for <strong>{org_name}</strong> is now <strong>{status}</strong>{tier_info}.</p>
        <p>Manage your subscription at <a href="https://cortaloom.ai/billing">CortaLoom Billing</a>.</p>
        <p style="color: #888; font-size: 12px;">CortaLoom AI — Automated Prior Authorization</p>
        """,
    )
