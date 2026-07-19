# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class KadWebsite(http.Controller):

    @http.route('/kad/contact', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def kad_contact(self, **post):
        """Receive contact form submissions and email the company."""
        name = (post.get('name') or '').strip()
        email = (post.get('email') or '').strip()
        phone = (post.get('phone') or '').strip()
        company = (post.get('company') or '').strip()
        message = (post.get('message') or '').strip()

        if name and email and message:
            body_html = (
                f"<p><strong>Name:</strong> {name}</p>"
                f"<p><strong>Email:</strong> {email}</p>"
                f"<p><strong>Phone:</strong> {phone or 'N/A'}</p>"
                f"<p><strong>Company:</strong> {company or 'N/A'}</p>"
                f"<p><strong>Message:</strong></p>"
                f"<p>{message}</p>"
            )
            email_to = request.env.company.email or 'info@kadglobaltrading.com'
            request.env['mail.mail'].sudo().create({
                'subject': f'KAD Website Contact — {name}',
                'email_from': request.env.company.email_formatted or email_to,
                'reply_to': email,
                'email_to': email_to,
                'body_html': body_html,
            }).send()

        return request.render('website_kad_global.contact_thanks')
