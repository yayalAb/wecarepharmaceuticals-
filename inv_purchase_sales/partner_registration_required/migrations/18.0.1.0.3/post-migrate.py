# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Fix partner form views + ensure registry picks up compatibility fields."""
    from odoo.addons.partner_registration_required.hooks import _fix_partner_views

    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_partner_views(env)
