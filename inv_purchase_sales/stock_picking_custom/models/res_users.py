# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    # Used by stock reports. The Sign app also defines this field when installed.
    sign_signature = fields.Binary(
        string="Digital Signature",
        copy=False,
        attachment=True,
    )
