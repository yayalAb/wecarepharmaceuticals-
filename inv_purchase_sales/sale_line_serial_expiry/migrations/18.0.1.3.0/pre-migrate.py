# -*- coding: utf-8 -*-
"""Single serial (lot_id / restrict_lot_id) -> multiple serials (lot_ids / restrict_lot_ids).

Runs before the new field definitions load: the relation tables are created here and
filled from the existing single-lot columns, so no selected serial is lost. The ORM
reuses these tables as they already exist.
"""

RELATIONS = [
    # (relation table, column1, column2, owner table, source column)
    ('sale_order_line_stock_lot_rel', 'sale_order_line_id', 'stock_lot_id', 'sale_order_line', 'lot_id'),
    ('account_move_line_stock_lot_rel', 'account_move_line_id', 'stock_lot_id', 'account_move_line', 'lot_id'),
    ('stock_move_restrict_lot_rel', 'move_id', 'lot_id', 'stock_move', 'restrict_lot_id'),
]


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    for rel, col1, col2, owner, source in RELATIONS:
        if not _column_exists(cr, owner, source):
            continue
        cr.execute(f"""
            CREATE TABLE IF NOT EXISTS {rel} (
                {col1} INTEGER NOT NULL REFERENCES {owner}(id) ON DELETE CASCADE,
                {col2} INTEGER NOT NULL REFERENCES stock_lot(id) ON DELETE CASCADE,
                PRIMARY KEY ({col1}, {col2})
            )
        """)
        cr.execute(f"CREATE INDEX IF NOT EXISTS {rel}_{col2}_idx ON {rel} ({col2})")
        cr.execute(f"""
            INSERT INTO {rel} ({col1}, {col2})
            SELECT id, {source} FROM {owner} WHERE {source} IS NOT NULL
            ON CONFLICT DO NOTHING
        """)
