# -*- coding: utf-8 -*-
from odoo import fields, models


class CustomerComplianceDocumentType(models.Model):
    _name = 'customer.compliance.document.type'
    _description = 'Customer Compliance Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_required = fields.Boolean(
        string='Required for Sales',
        default=False,
        help='When enabled, customers must have a non-expired document of this '
             'type before a Sales Order can be confirmed.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        help='Leave empty to share this document type across all companies.',
    )

    _sql_constraints = [
        (
            'code_uniq',
            'unique(code)',
            'Document type code must be unique.',
        ),
    ]
