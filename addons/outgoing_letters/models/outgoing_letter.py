import base64
import io
from PIL import Image, ImageChops

from odoo import api, fields, models, _
from odoo.exceptions import UserError


def _clean_logo_image(logo_data):
    """Trim excess transparent and white whitespace around logo artwork and remove background noise."""
    if not logo_data:
        return False
    try:
        if isinstance(logo_data, str):
            raw_bytes = base64.b64decode(logo_data.encode('ascii'))
        elif isinstance(logo_data, (bytes, bytearray)):
            try:
                raw_bytes = base64.b64decode(logo_data)
            except Exception:
                raw_bytes = bytes(logo_data)
        else:
            return logo_data

        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        w, h = img.size
        if w < 10 or h < 10:
            return logo_data

        pixels = img.load()
        # Find tight bounding box of visible artwork (threshold < 235 on any RGB channel or alpha > 30)
        min_x, min_y, max_x, max_y = w, h, 0, 0
        has_content = False
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a > 30 and (r < 235 or g < 235 or b < 235):
                    has_content = True
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y

        if not has_content or min_x > max_x or min_y > max_y:
            return logo_data

        pad = 4
        crop_box = (max(0, min_x - pad), max(0, min_y - pad), min(w, max_x + 1 + pad), min(h, max_y + 1 + pad))
        img = img.crop(crop_box)
        w, h = img.size
        pixels = img.load()

        # Convert off-white / near-white background noise to transparent
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if r > 238 and g > 238 and b > 238:
                    pixels[x, y] = (255, 255, 255, 0)

        out_io = io.BytesIO()
        img.save(out_io, format="PNG")
        return base64.b64encode(out_io.getvalue())
    except Exception:
        return logo_data


def _clean_signature_image(sig_data):
    """Clean signature image by trimming bounding box / vertical border lines

    and making background transparent.
    """
    if not sig_data:
        return False
    try:
        if isinstance(sig_data, str):
            raw_bytes = base64.b64decode(sig_data.encode('ascii'))
        elif isinstance(sig_data, (bytes, bytearray)):
            try:
                raw_bytes = base64.b64decode(sig_data)
            except Exception:
                raw_bytes = bytes(sig_data)
        else:
            return sig_data

        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        w, h = img.size
        if w < 10 or h < 10:
            return sig_data

        pixels = img.load()

        def is_line_col(x):
            count = 0
            for y in range(h):
                r, g, b, a = pixels[x, y]
                if a > 30 and (r < 230 or g < 230 or b < 230):
                    count += 1
            return count >= max(5, int(h * 0.35))

        left_cut = 0
        for x in range(min(20, w // 4)):
            if is_line_col(x):
                left_cut = x + 1

        right_cut = w
        for x in range(w - 1, max(w - 21, 3 * w // 4), -1):
            if is_line_col(x):
                right_cut = x

        def is_line_row(y):
            count = 0
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a > 30 and (r < 230 or g < 230 or b < 230):
                    count += 1
            return count >= max(5, int(w * 0.35))

        top_cut = 0
        for y in range(min(15, h // 4)):
            if is_line_row(y):
                top_cut = y + 1

        bottom_cut = h
        for y in range(h - 1, max(h - 16, 3 * h // 4), -1):
            if is_line_row(y):
                bottom_cut = y

        if left_cut > 0 or right_cut < w or top_cut > 0 or bottom_cut < h:
            img = img.crop((left_cut, top_cut, right_cut, bottom_cut))
            w, h = img.size
            pixels = img.load()

        # Convert off-white background to transparent
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if r > 230 and g > 230 and b > 230:
                    pixels[x, y] = (255, 255, 255, 0)

        out_io = io.BytesIO()
        img.save(out_io, format="PNG")
        return base64.b64encode(out_io.getvalue())
    except Exception:
        return sig_data


class OutgoingLetter(models.Model):
    _name = 'outgoing.letter'
    _description = 'Outgoing Letter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _get_cropped_logo(self):
        raw_logo = self.logo or self.company_logo or self.company_id.logo
        return _clean_logo_image(raw_logo)

    def _default_letter_header(self):
        from markupsafe import Markup
        company = self.env.company
        name = (company.name or 'KALKIDAN ABEBAW DERSO').upper()
        return Markup(
            '<div style="font-size: 19px; font-weight: 800; color: #0f172a; margin-bottom: 2px; line-height: 1.25; white-space: nowrap;">ቃልኪዳን አበባው ደርሶ</div>'
            f'<div style="font-size: 14.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; color: #0f172a; margin-bottom: 2px; line-height: 1.25;">{name}</div>'
            '<div style="font-size: 11.5px; color: #475569; line-height: 1.4; white-space: nowrap;">Addis Abeba, Ethiopia.</div>'
        )

    def _clean_letter_header(self):
        return self._default_letter_header()

    def _default_letter_footer(self):
        from markupsafe import Markup
        return Markup('''<div style="border-top: 1.5px solid #222; padding-top: 6px; text-align: center; font-size: 11px; line-height: 1.5; color: #222;">
    <p style="margin: 0;"><strong>E-mail:</strong> info@kadglobaltrading.com &nbsp;&nbsp;&nbsp; <strong>Website:</strong> https://kadglobaltrading.com/</p>
    <p style="margin: 0;"><strong>Tel:</strong> +251-911 357 216 / +251 970606160 / +251116687378</p>
    <p style="margin: 0;"><strong>Address:</strong> Addis Ababa: Ethiopia</p>
</div>''')

    def init(self):
        super().init()
        # Fix company partner street and contacts
        try:
            self.env.cr.execute("""
                UPDATE res_partner p
                SET street = 'Addis Ababa: Ethiopia',
                    city = 'Addis Ababa',
                    phone = '+251-911 357 216 / +251 970606160 / +251116687378',
                    email = 'info@kadglobaltrading.com',
                    website = 'https://kadglobaltrading.com/'
                FROM res_company c
                WHERE c.partner_id = p.id;
            """)
        except Exception:
            pass
        # Cleanly reset letter_header and letter_footer for all existing records
        footer_html = (
            '<div style="border-top: 1.5px solid #222; padding-top: 6px; text-align: center; font-size: 11px; line-height: 1.5; color: #222;">'
            '<p style="margin: 0;"><strong>E-mail:</strong> info@kadglobaltrading.com &nbsp;&nbsp;&nbsp; <strong>Website:</strong> https://kadglobaltrading.com/</p>'
            '<p style="margin: 0;"><strong>Tel:</strong> +251-911 357 216 / +251 970606160 / +251116687378</p>'
            '<p style="margin: 0;"><strong>Address:</strong> Addis Ababa: Ethiopia</p>'
            '</div>'
        )
        header_html = (
            '<div style="font-size: 19px; font-weight: 800; color: #0f172a; margin-bottom: 2px; line-height: 1.25; white-space: nowrap;">ቃልኪዳን አበባው ደርሶ</div>'
            '<div style="font-size: 14.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; color: #0f172a; margin-bottom: 2px; line-height: 1.25;">KALKIDAN ABEBAW DERSO</div>'
            '<div style="font-size: 11.5px; color: #475569; line-height: 1.4; white-space: nowrap;">Addis Abeba, Ethiopia.</div>'
        )
        try:
            self.env.cr.execute("""
                UPDATE outgoing_letter
                SET letter_header = %s,
                    letter_footer = %s;
            """, (header_html, footer_html))
        except Exception:
            pass
        # Tightly crop logos to remove dead canvas margins
        try:
            for comp in self.env['res.company'].search([]):
                if comp.logo:
                    cropped = _clean_logo_image(comp.logo)
                    if cropped and cropped != comp.logo:
                        comp.logo = cropped
            for letter in self.env['outgoing.letter'].search([('logo', '!=', False)]):
                cropped = _clean_logo_image(letter.logo)
                if cropped and cropped != letter.logo:
                    letter.logo = cropped
        except Exception:
            pass

    @api.model
    def _default_report_layout(self):
        company = self.env.company
        if company.external_report_layout_id:
            layout = self.env['report.layout'].search([('view_id.key', '=', company.external_report_layout_id.key)], limit=1)
            if layout:
                return layout.id
        layout = self.env['report.layout'].search([('name', '=', 'Light')], limit=1)
        if not layout:
            layout = self.env['report.layout'].search([], limit=1)
        return layout.id if layout else False

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True)
    title = fields.Char(string='Title', tracking=True)
    content = fields.Html(string='Content')
    greeting = fields.Char(
        string='Greeting',
        default='ከሰላምታ ጋር፣',
        tracking=True,
    )
    letter_header = fields.Html(
        string='Letter Header',
        default=_default_letter_header,
        sanitize=False,
    )
    letter_footer = fields.Html(
        string='Letter Footer',
        default=_default_letter_footer,
        sanitize=False,
    )
    date = fields.Date(
        string='Date', default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    company_logo = fields.Binary(
        related='company_id.logo', string='Company Logo', readonly=True)
    company_name = fields.Char(
        related='company_id.name', string='Company Name', readonly=True)

    # Document Layout & Styling (per letter, defaults from company)
    logo = fields.Binary(
        string='Logo',
        default=lambda self: self.env.company.logo,
        attachment=True,
    )
    report_layout_id = fields.Many2one(
        'report.layout',
        string='Document Layout',
        default=_default_report_layout,
        tracking=True,
    )
    layout_background = fields.Selection([
        ('Blank', 'Blank'),
        ('Geometric', 'Geometric'),
        ('Custom', 'Custom'),
    ], string='Layout Background', default=lambda self: self.env.company.layout_background or 'Blank', tracking=True)
    layout_background_image = fields.Binary(
        string='Background Image',
        default=lambda self: self.env.company.layout_background_image,
        attachment=True,
    )
    primary_color = fields.Char(
        string='Primary Color',
        default=lambda self: self.env.company.primary_color or '#1e293b',
    )
    secondary_color = fields.Char(
        string='Secondary Color',
        default=lambda self: self.env.company.secondary_color or '#475569',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('printable', 'Printable'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)
    approved_by_id = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False, tracking=True)
    approver_signature = fields.Binary(
        string='Approver Signature', compute='_compute_approver_info')
    approver_name = fields.Char(
        string='Approver Name', compute='_compute_approver_info')

    @api.depends('approved_by_id', 'state', 'write_uid', 'create_uid')
    def _compute_approver_info(self):
        for letter in self:
            approver = letter.approved_by_id or (letter.state in ('approved', 'printable') and (letter.write_uid or letter.create_uid))
            letter.approver_name = approver.name if approver else False
            sig = False
            if approver:
                if hasattr(approver, 'sign_signature') and approver.sign_signature:
                    sig = approver.sign_signature
                elif hasattr(approver, 'employee_id') and approver.employee_id and hasattr(approver.employee_id, 'emp_signature') and approver.employee_id.emp_signature:
                    sig = approver.employee_id.emp_signature
            letter.approver_signature = _clean_signature_image(sig) if sig else False

    def _check_state(self, allowed):
        for letter in self:
            if letter.state not in allowed:
                raise UserError(
                    _('This action is not allowed for letter "%s" in its current status.', letter.title))

    def _check_group(self, group_xmlid):
        if not self.env.user.has_group(group_xmlid):
            raise UserError(
                _('You do not have the rights to perform this action.'))

    @api.model
    def action_open_last_letter(self):
        last_letter = self.search([], order='write_date desc, id desc', limit=1)
        action = {
            'name': _('Outgoing Letters'),
            'type': 'ir.actions.act_window',
            'res_model': 'outgoing.letter',
            'views': [[False, 'form'], [False, 'list']],
            'target': 'current',
            'context': dict(self.env.context),
        }
        if last_letter:
            action['res_id'] = last_letter.id
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('outgoing.letter') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self._check_group('outgoing_letters.group_outgoing_letter_user')
        self._check_state(['draft'])
        self.state = 'submitted'

    def action_approve(self):
        self._check_group('outgoing_letters.group_outgoing_letter_approver')
        self._check_state(['submitted'])
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
        })

    def action_set_printable(self):
        self._check_group('outgoing_letters.group_outgoing_letter_approver')
        self._check_state(['approved'])
        self.state = 'printable'

    def action_reset_to_draft(self):
        self._check_group('outgoing_letters.group_outgoing_letter_approver')
        self._check_state(['submitted', 'approved', 'printable'])
        self.write({
            'state': 'draft',
            'approved_by_id': False,
        })

    def action_print(self):
        self.ensure_one()
        self._check_group('outgoing_letters.group_outgoing_letter_user')
        self._check_state(['printable'])
        if not self.name or self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code(
                'outgoing.letter') or _('New')
        pdf_content, __ = self.env['ir.actions.report']._render_qweb_pdf(
            'outgoing_letters.action_report_outgoing_letter', self.ids)
        attachment = self.env['ir.attachment'].create({
            'name': 'Letter - %s.pdf' % self.name.replace('/', '-'),
            'type': 'binary',
            'raw': pdf_content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.message_post(
            body=_('Letter printed with reference %s', self.name),
            attachment_ids=attachment.ids)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
