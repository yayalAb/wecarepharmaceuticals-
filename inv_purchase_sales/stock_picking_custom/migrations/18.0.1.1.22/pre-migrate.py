# -*- coding: utf-8 -*-
"""
Migration 18.0.1.1.22 — Add line_unit_price and line_subtotal columns to stock_move.

These are stored computed fields added to stock.move in stock_picking_custom.
If the module was installed before these fields were added, the columns will be
missing from the database, causing an UndefinedColumn error at runtime.
"""


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE stock_move
            ADD COLUMN IF NOT EXISTS line_unit_price NUMERIC,
            ADD COLUMN IF NOT EXISTS line_subtotal   NUMERIC
    """)
