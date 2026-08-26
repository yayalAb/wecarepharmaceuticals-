# -*- coding: utf-8 -*-
"""Ensure company MRC column exists before ORM loads res.company."""


def migrate(cr, version):
    cr.execute(
        """
            ALTER TABLE res_company
            ADD COLUMN IF NOT EXISTS invoice_mrc_no VARCHAR
        """
    )
