# -*- coding: utf-8 -*-
import base64
import re
from urllib.parse import quote

from odoo import api, fields, models
from odoo.exceptions import UserError

DEFAULT_MESSAGES = {
    'sale.order': (
        'Dear Customer,\n'
        'Please find attached Sales Order {name} from {company}.\n'
        'Thank you.'
    ),
    'account.move': (
        'Dear Customer,\n'
        'Please find attached {name} from {company}.\n'
        'Thank you.'
    ),
    'stock.picking': (
        'Dear Customer,\n'
        'Please find attached Delivery Order {name}.\n'
        'Thank you.'
    ),
    'purchase.order': (
        'Dear Supplier,\n'
        'Please find attached Purchase Order {name} from {company}.\n'
        'Kindly confirm receipt.'
    ),
    'account.payment': (
        'Dear Customer,\n'
        'Please find attached Payment Receipt {name} from {company}.\n'
        'Thank you.'
    ),
    'supplies.rfp': (
        'Dear Supplier,\n'
        'Please find attached Purchase Request {name} from {company}.\n'
        'Kindly confirm receipt.'
    ),
    'stock.scrap': (
        'Dear Team,\n'
        'Please find attached Inventory Adjustment / Scrap {name} from {company}.\n'
        'Thank you.'
    ),
    'store.request': (
        'Dear Team,\n'
        'Please find attached Store Request {name} from {company}.\n'
        'Thank you.'
    ),
}


class WecareShareMediaWizard(models.TransientModel):
    _name = 'wecare.share.media.wizard'
    _description = 'Share to Media'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    document_name = fields.Char(string='Document', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Recipient')
    channel = fields.Selection(
        [
            ('whatsapp', 'WhatsApp'),
            ('telegram', 'Telegram'),
        ],
        required=True,
        default='whatsapp',
    )
    phone = fields.Char(string='Phone / WhatsApp')
    telegram_username = fields.Char(string='Telegram Username')
    message = fields.Text(required=True)
    report_xmlid = fields.Char()
    attachment_id = fields.Many2one('ir.attachment', string='PDF', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        res_model = res.get('res_model') or ctx.get('default_res_model')
        res_id = res.get('res_id') or ctx.get('default_res_id')
        partner = self.env['res.partner'].browse(res.get('partner_id') or ctx.get('default_partner_id'))
        if partner:
            res.setdefault('phone', partner.mobile or partner.phone)
            res.setdefault('telegram_username', partner.telegram_username)
        if res_model and res_id and 'message' in fields_list and not res.get('message'):
            record = self.env[res_model].browse(res_id)
            template = DEFAULT_MESSAGES.get(res_model, DEFAULT_MESSAGES['sale.order'])
            if res_model == 'account.move':
                move_type = record.move_type
                if move_type == 'in_invoice':
                    template = (
                        'Dear Supplier,\n'
                        'Please find attached Vendor Bill {name} from {company}.\n'
                        'Kindly confirm receipt.'
                    )
                elif move_type == 'out_refund':
                    template = (
                        'Dear Customer,\n'
                        'Please find attached Credit Note {name} from {company}.\n'
                        'Thank you.'
                    )
                elif move_type == 'in_refund':
                    template = (
                        'Dear Supplier,\n'
                        'Please find attached Vendor Credit Note {name} from {company}.\n'
                        'Thank you.'
                    )
            elif res_model == 'purchase.order' and record.state in ('draft', 'sent'):
                template = (
                    'Dear Supplier,\n'
                    'Please find attached RFQ {name} from {company}.\n'
                    'Kindly confirm receipt.'
                )
            elif res_model == 'account.payment' and record.payment_type == 'outbound':
                template = (
                    'Dear Supplier,\n'
                    'Please find attached Payment {name} from {company}.\n'
                    'Kindly confirm receipt.'
                )
            res['message'] = template.format(
                name=record.display_name,
                company=record.company_id.name if 'company_id' in record._fields else self.env.company.name,
            )
            res.setdefault('document_name', record.display_name)
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone = self.partner_id.mobile or self.partner_id.phone
            self.telegram_username = self.partner_id.telegram_username

    def _get_record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    def _render_pdf(self):
        self.ensure_one()
        xmlid = self.report_xmlid
        if not xmlid:
            return False
        try:
            pdf_content, _dummy = self.env['ir.actions.report']._render_qweb_pdf(
                xmlid, [self.res_id]
            )
        except Exception:
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if not report:
                return False
            pdf_content, _dummy = self.env['ir.actions.report']._render_qweb_pdf(
                report, [self.res_id]
            )
        filename = '%s.pdf' % (self.document_name or 'document').replace('/', '-')
        datas = pdf_content if isinstance(pdf_content, str) else base64.b64encode(pdf_content)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': datas,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'mimetype': 'application/pdf',
        })
        self.attachment_id = attachment
        return attachment

    def action_download_pdf(self):
        self._render_pdf()
        if not self.attachment_id:
            raise UserError(self.env._('No PDF report is configured for this document.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.attachment_id.id,
            'target': 'self',
        }

    def _clean_phone(self, phone):
        digits = re.sub(r'\D', '', phone or '')
        if digits.startswith('0') and len(digits) == 10:
            digits = '251' + digits[1:]
        return digits

    def _share_url(self):
        self.ensure_one()
        text = quote(self.message or '')
        if self.channel == 'whatsapp':
            phone = self._clean_phone(self.phone)
            if not phone:
                raise UserError(self.env._('Enter a WhatsApp phone number for the recipient.'))
            return 'https://wa.me/%s?text=%s' % (phone, text)
        username = (self.telegram_username or '').replace('@', '').strip()
        if not username:
            raise UserError(self.env._('Enter a Telegram username for the recipient.'))
        return 'https://t.me/%s' % username

    def action_send(self):
        self.ensure_one()
        if not self.attachment_id:
            try:
                self._render_pdf()
            except Exception:
                pass
        self.env['wecare.share.history'].create({
            'res_model': self.res_model,
            'res_id': self.res_id,
            'document_name': self.document_name,
            'channel': self.channel,
            'partner_id': self.partner_id.id,
            'phone': self.phone or self.telegram_username,
            'message': self.message,
            'attachment_id': self.attachment_id.id,
        })
        record = self._get_record()
        if 'message_post' in dir(record):
            record.message_post(
                body=self.env._(
                    'Shared to %(channel)s (%(partner)s).<br/>%(message)s',
                    channel=dict(self._fields['channel'].selection).get(self.channel),
                    partner=self.partner_id.display_name or self.phone or self.telegram_username,
                    message=(self.message or '').replace('\n', '<br/>'),
                ),
                attachment_ids=self.attachment_id.ids if self.attachment_id else [],
            )
        return {
            'type': 'ir.actions.act_url',
            'url': self._share_url(),
            'target': 'new',
        }
