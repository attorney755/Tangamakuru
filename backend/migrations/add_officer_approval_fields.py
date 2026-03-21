"""Add officer approval fields to users table

Revision ID: add_officer_approval_fields
Revises: (your previous migration)
Create Date: 2024-03-17
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_officer_approval_fields'
down_revision = None  # Replace with your previous migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to users table
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('approval_status', sa.String(20), server_default='pending', nullable=False))
    op.add_column('users', sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('users', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('denied_reason', sa.Text(), nullable=True))
    
    # Create pending_approvals table
    op.create_table('pending_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('officer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('admin_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('email_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('denial_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_approvals_officer_id'), 'pending_approvals', ['officer_id'], unique=False)
    op.create_index(op.f('ix_pending_approvals_admin_id'), 'pending_approvals', ['admin_id'], unique=False)

def downgrade():
    # Remove columns from users table
    op.drop_column('users', 'is_approved')
    op.drop_column('users', 'approval_status')
    op.drop_column('users', 'approved_by')
    op.drop_column('users', 'approved_at')
    op.drop_column('users', 'denied_reason')
    
    # Drop pending_approvals table
    op.drop_table('pending_approvals')