import os
import sys
from pathlib import Path
from datetime import datetime, timezone

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)
from reportlab.pdfgen import canvas

SCREENSHOTS_DIR = Path(r"C:\Users\tmmud\.gemini\antigravity\scratch\guardrail\screenshots")
REPORT_NAME = "GuardRail_Fraud_Alert_Triage_Console_Report.pdf"

DESTINATIONS = [
    Path(r"C:\Users\tmmud\OneDrive\Desktop\Downloads") / REPORT_NAME,
    Path(r"C:\Users\tmmud\Desktop\Downloads") / REPORT_NAME,
    Path(r"C:\Users\tmmud\Downloads") / REPORT_NAME,
    Path(r"C:\Users\tmmud\OneDrive\Desktop") / REPORT_NAME,
]

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

class CleanNumberedCanvas(canvas.Canvas):
    """Clean two-pass canvas for editorial report styling with page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        if self._pageNumber == 1:
            return  # Skip header/footer on title page

        self.saveState()
        # Top Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1E293B")) # Dark Slate
        self.drawString(36, PAGE_HEIGHT - 22, "GuardRail")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(82, PAGE_HEIGHT - 22, "|  Fraud Alert Triage Console  •  Engineering Walkthrough")
        
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, PAGE_HEIGHT - 26, PAGE_WIDTH - 36, PAGE_HEIGHT - 26)

        # Bottom Footer
        self.line(36, 26, PAGE_WIDTH - 36, 26)
        self.drawString(36, 16, "GuardRail Platform Walkthrough  •  Built with FastAPI, Kafka, PostgreSQL, Redis, and React")
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(PAGE_WIDTH - 36, 16, page_str)
        self.restoreState()


def build_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()

    # Editorial Light Theme Typography
    title_style = ParagraphStyle(
        'EditorialTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0F172A")
    )
    subtitle_style = ParagraphStyle(
        'EditorialSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#334155")
    )
    heading_style = ParagraphStyle(
        'EditorialHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A")
    )
    meta_tag_style = ParagraphStyle(
        'MetaTag',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#2563EB")
    )
    body_style = ParagraphStyle(
        'EditorialBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    callout_num_style = ParagraphStyle(
        'CalloutNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1D4ED8")
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )
    table_hdr_style = ParagraphStyle(
        'TableHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.white
    )

    story = []

    # =========================================================================
    # PAGE 1: COVER & PRODUCT SUMMARY
    # =========================================================================
    story.append(Spacer(1, 15))
    
    # Category Tag
    tag_table = Table(
        [[Paragraph("<b>PROTOTYPE WALKTHROUGH  •  SIMULATED FINANCIAL OPERATIONS DATA</b>", meta_tag_style)]],
        colWidths=[380],
        style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#1D4ED8")),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ]
    )
    story.append(tag_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("GuardRail: a fraud alert triage console", title_style))
    story.append(Spacer(1, 6))

    intro_text = (
        "Fraud analysts need to know what to investigate next, and two people shouldn't work the same case. "
        "GuardRail ranks alerts by urgency and lets one analyst claim each case using atomic database locking with leases. "
        "Built with FastAPI, Apache Kafka, PostgreSQL, Redis, and React. "
        "This is an engineering prototype running on simulated banking transaction data."
    )
    story.append(Paragraph(intro_text, subtitle_style))
    story.append(Spacer(1, 12))

    # Problem vs Solution Grid
    problem_grid = [
        [
            Paragraph("<b>Problem in Fraud Operations</b>", table_hdr_style),
            Paragraph("<b>GuardRail Implementation</b>", table_hdr_style),
            Paragraph("<b>Architecture & Tech Choice</b>", table_hdr_style),
        ],
        [
            Paragraph("<b>Duplicate Investigation Collisions:</b> Multiple analysts open the same high-severity alert simultaneously, duplicating effort and risking contradictory customer contact.", table_cell_style),
            Paragraph("<b>Atomic Claim Locking:</b> Row-level locking (SELECT FOR UPDATE) acquires a 10-minute lease. Other analysts receive HTTP 409 Conflict. If abandoned, a background reaper releases the claim.", table_cell_style),
            Paragraph("PostgreSQL ACID transaction + conditional update. PostgreSQL is the source of truth, avoiding Redis split-brain risks.", table_cell_style),
        ],
        [
            Paragraph("<b>Unassigned Alerts Missing SLAs:</b> Critical alerts get buried under volume while analysts work easier low-risk cases, causing regulatory SLA breaches.", table_cell_style),
            Paragraph("<b>Dynamic Urgency Sorting & Auto-Escalation:</b> Queue orders by remaining SLA seconds and fraud score. An asynchronous worker elevates unhandled alerts to P1 Critical as deadlines approach.", table_cell_style),
            Paragraph("FastAPI background worker + SLA Engine. Alerts are auto-prioritized in real-time.", table_cell_style),
        ],
        [
            Paragraph("<b>Duplicate Events on Retries:</b> Kafka at-least-once delivery can cause network replay, creating ghost cases and skewing financial risk metrics.", table_cell_style),
            Paragraph("<b>Deduplication Constraint:</b> Unique event_id database constraint with ON CONFLICT DO NOTHING ensures effectively-once business processing.", table_cell_style),
            Paragraph("Transactional outbox pattern + PostgreSQL idempotency key. Safely ignores repeated Kafka message keys.", table_cell_style),
        ],
        [
            Paragraph("<b>Poison Messages Choking Consumers:</b> Malformed payloads or failing downstream scoring dependencies block consumer partitions.", table_cell_style),
            Paragraph("<b>Circuit Breaker & DLQ Replay:</b> 3-state circuit breaker fast-fails when scoring times out. Unrecoverable messages route to fraud.alerts.dlq for isolated forensics and operator replay.", table_cell_style),
            Paragraph("Custom 3-state circuit breaker (CLOSED, OPEN, HALF_OPEN) + partitioned Kafka DLQ topic.", table_cell_style),
        ],
    ]
    grid_table = Table(
        problem_grid,
        colWidths=[240, 290, 239],
        style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]
    )
    story.append(grid_table)
    story.append(Spacer(1, 12))

    # Metadata & Demo Access Card
    meta_data = [
        [
            Paragraph("<b>Local Dev Server:</b> http://localhost:3000", table_cell_style),
            Paragraph("<b>API Docs:</b> http://127.0.0.1:8000/docs", table_cell_style),
            Paragraph("<b>Test Suite:</b> 11/11 Passed (pytest)", table_cell_style),
            Paragraph("<b>Demo Login:</b> admin@guardrail.io / Password123!", table_cell_style)
        ]
    ]
    meta_table = Table(
        meta_data,
        colWidths=[192, 192, 192, 193],
        style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]
    )
    story.append(meta_table)

    story.append(PageBreak())

    # =========================================================================
    # SCREENSHOT WALKTHROUGH PAGES
    # =========================================================================
    walkthrough_pages = [
        {
            "num": "01",
            "title": "Live Alert Triage Queue: Urgency Sorting & Atomic Claiming",
            "tag": "QUEUE MANAGEMENT  •  POSTGRESQL ROW LOCKING  •  SLA PRIORITIZATION",
            "description": (
                "<b>1. View Tabs:</b> Triage queue defaults to active cases with quick tabs for All Active (205), Unassigned (140), "
                "Escalated (12), and Resolved Today (45).<br/>"
                "<b>2. Prominent Anomaly Reasons:</b> Full fraud explanation is displayed without truncation (e.g. unusually large purchase vs customer baseline, crypto cashout via proxy, impossible geo-velocity).<br/>"
                "<b>3. Live SLA Countdown:</b> Displays exact time remaining or overdue duration (e.g. '34m remaining' or '14m overdue'). Healthy alerts remain green/amber; breached alerts are highlighted in red.<br/>"
                "<b>4. Atomic Claim Action:</b> Clicking 'Claim' acquires an exclusive 10-minute lease. Row click opens the deep-dive investigation drawer."
            ),
            "image": "03_live_triage_queue.png",
        },
        {
            "num": "02",
            "title": "Investigation Drawer: Evidence, Risk Factor Breakdown & Resolution",
            "tag": "FRAUD SCORING BREAKDOWN  •  LEASE TIMERS  •  DECISION WORKFLOW",
            "description": (
                "<b>1. Granular Risk Factor Breakdown:</b> Displays composite score with itemized factor contributions (e.g. Velocity Burst +35, Geo-Distance +25, Unregistered Device +15).<br/>"
                "<b>2. Claim Lease Countdown:</b> Displays active 10-minute lease timer with one-click 'Release Claim' and 'Renew Lease' controls to prevent case hoarding.<br/>"
                "<b>3. Customer & Transaction Evidence:</b> Transaction amount, currency, customer ID, merchant details, cardholder profile, and device fingerprint.<br/>"
                "<b>4. Decision Actions:</b> Analysts record resolution reasons ('Confirm Fraud', 'False Positive', 'Escalate to Tier 2') with mandatory audit notes."
            ),
            "image": "04_alert_investigation_drawer.png",
        },
        {
            "num": "03",
            "title": "Operations Dashboard: Cluster Telemetry & SLA Compliance",
            "tag": "SLA HEALTH DISTRIBUTION  •  INGESTION VELOCITY  •  WEBSOCKET TELEMETRY",
            "description": (
                "<b>1. Balanced Operational Telemetry:</b> Shows 205 active alerts with a realistic health profile: 140 healthy (68%), 48 approaching warning (23%), and 12 breached (6%).<br/>"
                "<b>2. Consistent Throughput Metrics:</b> Displays 1.05 alerts/min throughput, matching the hourly volume chart (peak ~62 alerts/hour) and 250 processed today.<br/>"
                "<b>3. Realistic Resolution Velocity:</b> Displays 12.2m average resolution time calculated from 45 alerts investigated and resolved today.<br/>"
                "<b>4. Circuit Breaker Header:</b> Displays live status of the external scoring circuit breaker (CLOSED, 0 rejected calls)."
            ),
            "image": "02_operations_dashboard.png",
        },
        {
            "num": "04",
            "title": "Analyst Workload Table: Team Capacity & Case Allocation",
            "tag": "CAPACITY MANAGEMENT  •  RESOLUTION VELOCITY  •  SUPERVISORY REASSIGNMENT",
            "description": (
                "<b>1. Tabular Capacity Overview:</b> Replaces slow cards with a sortable table detailing analyst name, role, operational team, and active claim count.<br/>"
                "<b>2. Individual Performance Metrics:</b> Displays varied, realistic speed and compliance metrics per analyst based on experience tier (Sarah Chen: 8.2m / 98.4%; David Kim: 13.6m / 93.2%).<br/>"
                "<b>3. Governance vs Triage Separation:</b> Administrator account is clearly designated as 'Governance & SecOps (No Triage Quota)' to prevent false capacity assumptions.<br/>"
                "<b>4. Direct Case Navigation:</b> 'View Cases' link navigates directly to alerts currently claimed by that analyst for supervisor review."
            ),
            "image": "05_analyst_workload.png",
        },
        {
            "num": "05",
            "title": "Failed Events (DLQ): Poison Pill Quarantine & Controlled Replay",
            "tag": "DEAD LETTER QUEUE  •  SCHEMA ISOLATION  •  OPERATOR REPLAY CONTROLS",
            "description": (
                "<b>1. Isolated Failure States:</b> Distinguishes between PENDING (transient scoring timeouts, ready for replay), PROCESSING (inflight), and SUCCEEDED (replayed).<br/>"
                "<b>2. Quarantined Schema Errors:</b> Malformed currency ('USDD') and JSON decode errors are flagged as FAILED_VALIDATION with 0 retries and disabled replay until code is patched.<br/>"
                "<b>3. Guarded Replay Button:</b> 'Replay Pending (3)' button is active only for transient pending events; disabled when no items are pending.<br/>"
                "<b>4. Payload Inspection:</b> Inspect button displays raw JSON payload, partition offset, and consumer stack trace."
            ),
            "image": "06_dead_letter_queue.png",
        },
        {
            "num": "06",
            "title": "System Health & Observability: Circuit Breaker & Dependency Matrix",
            "tag": "CIRCUIT BREAKER TELEMETRY  •  HEALTH CHECKS  •  LATENCY MONITORING",
            "description": (
                "<b>1. Cluster Status (HEALTHY):</b> All core dependencies verified UP with live latencies: PostgreSQL (1.85 ms), Redis Cache (0.45 ms), Apache Kafka KRaft (1.12 ms).<br/>"
                "<b>2. Circuit Breaker Telemetry:</b> Shows real call metrics: 2,840 total calls, 2,836 successful calls (99.86%), 4 failed calls, 0 rejected, state: CLOSED.<br/>"
                "<b>3. Realistic Fallback Details:</b> Explains active fallbacks (e.g. in-memory cache tier, KRaft internal ring-buffer) when standalone execution is active.<br/>"
                "<b>4. Active WebSocket Count:</b> Monitors real-time connected analyst sessions receiving live alert broadcasts."
            ),
            "image": "07_system_health.png",
        },
        {
            "num": "07",
            "title": "Authentication & RBAC: Multi-Tier Access Perimeter",
            "tag": "JWT SESSION MANAGEMENT  •  BCRYPT SECURITY  •  DEMO ENVIRONMENT NOTICE",
            "description": (
                "<b>1. Role-Based Access Control:</b> Enforces RBAC permissions across Administrator, Fraud Supervisor, Senior Analyst, and Fraud Analyst tiers.<br/>"
                "<b>2. Clear Demo Environment Labeling:</b> Quick-fill profile switcher is explicitly labeled 'Demo Environment (Non-Production)' with enterprise SSO notice.<br/>"
                "<b>3. Cryptographic Storage:</b> Passwords hashed using bcrypt; sessions signed using HS256 JWT tokens with 60-minute expiry.<br/>"
                "<b>4. Consistent Navigation:</b> Authenticated sessions preserve role-aware sidebar items across all pages."
            ),
            "image": "01_login_page.png",
        },
    ]

    img_w = PAGE_WIDTH - 72   # 769 pt
    img_h = 340               # 340 pt fits cleanly with text headers on landscape A4

    for idx, item in enumerate(walkthrough_pages):
        # Section Category Badge
        story.append(Paragraph(f"<b>SCREEN {item['num']}  •  {item['tag']}</b>", meta_tag_style))
        story.append(Spacer(1, 2))
        
        # Section Title
        story.append(Paragraph(item['title'], heading_style))
        story.append(Spacer(1, 4))

        # Description Card
        desc_card = Table(
            [[Paragraph(item['description'], body_style)]],
            colWidths=[PAGE_WIDTH - 72],
            style=[
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]
        )
        story.append(desc_card)
        story.append(Spacer(1, 6))

        # Screenshot Image with Clean Border
        img_path = SCREENSHOTS_DIR / item['image']
        if img_path.exists():
            img_table = Table(
                [[Image(str(img_path), width=img_w - 4, height=img_h)]],
                colWidths=[img_w],
                style=[
                    ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#070A11")),
                    ('PADDING', (0, 0), (-1, -1), 1),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ]
            )
            story.append(img_table)
        else:
            story.append(Paragraph(f"[Missing Screenshot: {item['image']}]", body_style))

        if idx < len(walkthrough_pages) - 1:
            story.append(PageBreak())

    # Build PDF with clean two-pass canvas
    doc.build(story, canvasmaker=CleanNumberedCanvas)
    print(f"Generated clean PDF report: {output_path}")


def main():
    primary_target = DESTINATIONS[0]
    build_pdf(primary_target)

    # Distribute to all other destination directories
    import shutil
    for dest in DESTINATIONS[1:]:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(primary_target, dest)
            print(f"Copied to: {dest}")
        except Exception as e:
            print(f"Failed to copy to {dest}: {e}")

if __name__ == "__main__":
    main()
