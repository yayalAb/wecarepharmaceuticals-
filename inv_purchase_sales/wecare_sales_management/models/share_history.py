# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WecareShareHistory(models.Model):
    _name = 'wecare.share.history'
    _description = 'Share to Media History'
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    document_name = fields.Char(string='Document')
    channel = fields.Selection(
        [
            ('whatsapp', 'WhatsApp'),
            ('telegram', 'Telegram'),
        ],
        required=True,
    )
    partner_id = fields.Many2one('res.partner', string='Recipient')
    phone = fields.Char()
    message = fields.Text()
    attachment_id = fields.Many2one('ir.attachment', string='PDF')
    user_id = fields.Many2one(
        'res.users',
        string='Shared By',
        default=lambda self: self.env.user,
        required=True,
    )
    share_date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    @api.depends('document_name', 'channel', 'partner_id')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s · %s · %s' % (
                rec.document_name or rec.res_model,
                dict(rec._fields['channel'].selection).get(rec.channel) or '',
                rec.partner_id.display_name or '',
            )
