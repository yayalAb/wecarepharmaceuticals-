# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    fs_no = fields.Char(
        string='FS No',
        copy=False,
        readonly=True,
        default=False,
        help='Sequence number assigned when a customer invoice is posted.',
    )
    mrc_no = fields.Char(
        string='MRC No',
        help='Fixed MRC number from company configuration.',
    )
    payment_method = fields.Selection(
        selection=[
            ('cash', 'Cash'),
            ('credit', 'Credit'),
        ],
        string='Payment Method',
    )

    def _is_customer_invoice_for_fs_mrc(self):
        self.ensure_one()
        return self.move_type in ('out_invoice', 'out_refund')

    def _assign_fs_no(self):
        """Assign next FS sequence when missing on customer invoices."""
        sequence = self.env['ir.sequence']
        for move in self:
            if not move._is_customer_invoice_for_fs_mrc() or move.fs_no:
                continue
            move.fs_no = sequence.next_by_code(
                'account.move.fs.no',
                sequence_date=move.invoice_date or fields.Date.context_today(move),
            ) or '/'

    def _assign_mrc_no_from_company(self):
        """Apply the configured company MRC No when the invoice has none."""
        for move in self:
            if not move._is_customer_invoice_for_fs_mrc() or move.mrc_no:
                continue
            move.mrc_no = move.company_id.invoice_mrc_no or False

    @api.model_create_multi
    def create(self, vals_list):
        customer_types = {'out_invoice', 'out_refund'}
        for vals in vals_list:
            move_type = vals.get('move_type')
            if move_type in customer_types and not vals.get('mrc_no'):
                company = self.env['res.company'].browse(
                    vals.get('company_id') or self.env.company.id
                )
                if company.invoice_mrc_no:
                    vals['mrc_no'] = company.invoice_mrc_no
        return super().create(vals_list)

    def action_post(self):
        missing = self.filtered(
            lambda m: m.move_type in ('out_invoice', 'out_refund')
            and not m.payment_method
        )
        if missing:
            raise UserError(_(
                'Please select a Payment Method before posting: %s',
                ', '.join(missing.mapped('display_name')),
            ))
        return super().action_post()

    def _post(self, soft=True):
        # FS No is only consumed once the invoice is actually posted (never on drafts).
        posted = super()._post(soft=soft)
        to_fix = posted.filtered(
            lambda m: m.move_type in ('out_invoice', 'out_refund')
        )
        to_fix._assign_mrc_no_from_company()
        to_fix.filtered(lambda m: not m.fs_no)._assign_fs_no()
        return posted

    def refresh_invoice_currency_rate(self):
        """Support legacy invoice form buttons from Studio or older customizations."""
        self._compute_invoice_currency_rate()
        self.line_ids._compute_currency_rate()
        return True
