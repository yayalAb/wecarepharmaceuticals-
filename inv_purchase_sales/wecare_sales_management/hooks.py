# -*- coding: utf-8 -*-
from odoo.addons.sale_line_serial_expiry.hooks import _strip_stale_currency_rate_xpath


def pre_init_hook(env):
    _strip_stale_currency_rate_xpath(env)
