# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Existing documents were already in use for sales: start them as Approved."""
    if not version:
        return
    cr.execute("""
        ALTER TABLE customer_compliance_document
        ADD COLUMN IF NOT EXISTS state varchar
    """)
    cr.execute("""
        UPDATE customer_compliance_document
           SET state = 'approved'
         WHERE state IS NULL
    """)
