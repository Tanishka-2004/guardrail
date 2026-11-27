"""Initial migration for GuardRail tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Analysts table
    op.create_table(
        'analysts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('team', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('workload_limit', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysts_email'), 'analysts', ['email'], unique=True)

    # Fraud Alerts table
    op.create_table(
        'fraud_alerts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('transaction_id', sa.String(length=128), nullable=False),
        sa.Column('customer_id', sa.String(length=128), nullable=False),
        sa.Column('merchant_id', sa.String(length=128), nullable=False),
        sa.Column('transaction_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('transaction_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fraud_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=30), nullable=False),
        sa.Column('fraud_reason', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('priority', sa.String(length=30), nullable=False),
        sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sla_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('assigned_analyst_id', sa.String(length=36), nullable=True),
        sa.Column('claimed_by', sa.String(length=255), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claim_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_reason', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('replay_count', sa.Integer(), nullable=False),
        sa.Column('source_event_metadata', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_analyst_id'], ['analysts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fraud_alerts_event_id'), 'fraud_alerts', ['event_id'], unique=True)
    op.create_index(op.f('ix_fraud_alerts_transaction_id'), 'fraud_alerts', ['transaction_id'])
    op.create_index(op.f('ix_fraud_alerts_customer_id'), 'fraud_alerts', ['customer_id'])
    op.create_index(op.f('ix_fraud_alerts_transaction_timestamp'), 'fraud_alerts', ['transaction_timestamp'])
    op.create_index(op.f('ix_fraud_alerts_status'), 'fraud_alerts', ['status'])
    op.create_index(op.f('ix_fraud_alerts_priority'), 'fraud_alerts', ['priority'])
    op.create_index(op.f('ix_fraud_alerts_sla_deadline'), 'fraud_alerts', ['sla_deadline'])
    op.create_index(op.f('ix_fraud_alerts_assigned_analyst_id'), 'fraud_alerts', ['assigned_analyst_id'])
    op.create_index(op.f('ix_fraud_alerts_claim_expires_at'), 'fraud_alerts', ['claim_expires_at'])
    op.create_index(op.f('ix_fraud_alerts_created_at'), 'fraud_alerts', ['created_at'])
    op.create_index('ix_fraud_alerts_status_priority', 'fraud_alerts', ['status', 'priority'])
    op.create_index('ix_fraud_alerts_sla_status', 'fraud_alerts', ['status', 'sla_deadline'])
    op.create_index('ix_fraud_alerts_claimed_expires', 'fraud_alerts', ['claimed_by', 'claim_expires_at'])

    # Audit log table
    op.create_table(
        'alert_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('alert_id', sa.String(length=36), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=True),
        sa.Column('actor_name', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('previous_state', sa.JSON(), nullable=False),
        sa.Column('new_state', sa.JSON(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['fraud_alerts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_audit_logs_alert_id'), 'alert_audit_logs', ['alert_id'])
    op.create_index(op.f('ix_alert_audit_logs_action'), 'alert_audit_logs', ['action'])
    op.create_index(op.f('ix_alert_audit_logs_timestamp'), 'alert_audit_logs', ['timestamp'])
    op.create_index('ix_audit_alert_timestamp', 'alert_audit_logs', ['alert_id', 'timestamp'])

    # Dead letter events table
    op.create_table(
        'dead_letter_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('original_event_id', sa.String(length=128), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('partition', sa.Integer(), nullable=False),
        sa.Column('offset', sa.Integer(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('error_type', sa.String(length=100), nullable=False),
        sa.Column('error_message', sa.String(length=1000), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('replay_status', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('replayed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dead_letter_events_original_event_id'), 'dead_letter_events', ['original_event_id'])
    op.create_index(op.f('ix_dead_letter_events_replay_status'), 'dead_letter_events', ['replay_status'])
    op.create_index(op.f('ix_dead_letter_events_created_at'), 'dead_letter_events', ['created_at'])
    op.create_index('ix_dlq_status_created', 'dead_letter_events', ['replay_status', 'created_at'])

    # Outbox table
    op.create_table(
        'alert_outbox',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('aggregate_id', sa.String(length=128), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_outbox_aggregate_id'), 'alert_outbox', ['aggregate_id'])
    op.create_index(op.f('ix_alert_outbox_created_at'), 'alert_outbox', ['created_at'])
    op.create_index(op.f('ix_alert_outbox_published_at'), 'alert_outbox', ['published_at'])
    op.create_index('ix_outbox_unprocessed', 'alert_outbox', ['published_at', 'created_at'])

def downgrade() -> None:
    op.drop_table('alert_outbox')
    op.drop_table('dead_letter_events')
    op.drop_table('alert_audit_logs')
    op.drop_table('fraud_alerts')
    op.drop_table('analysts')
