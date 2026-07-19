# -*- coding: utf-8 -*-

def pre_init_hook(cr):
    """Remove a broken inherited view left by a failed install attempt."""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.ui.view'].search([
        ('name', '=', 'res.partner.form.registration.required'),
    ]).unlink()
