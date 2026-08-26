# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    from odoo.addons.partner_registration_required.hooks import (
        _deactivate_views_from_missing_modules,
        _fix_partner_views,
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_partner_views(env)
    _deactivate_views_from_missing_modules(env)
