# -*- coding: utf-8 -*-
import re


def _strip_stale_currency_rate_xpath(env):
    """Odoo 18 invoice form no longer has refresh_invoice_currency_rate.

    An older stock_picking_custom inherit still targets that button. Installing
    another account.move form inherit re-validates the combined view and fails
    unless the stored arch is cleaned first.
    """
    view = env.ref(
        'stock_picking_custom.view_move_form_fs_mrc_payment',
        raise_if_not_found=False,
    )
    if not view:
        return
    arch = view.arch_db or ''
    if 'refresh_invoice_currency_rate' not in arch:
        return
    cleaned = re.sub(
        r'\s*<xpath\b[^>]*refresh_invoice_currency_rate[^>]*/>',
        '',
        arch,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r'\s*<xpath\b[^>]*refresh_invoice_currency_rate[^>]*>\s*</xpath>',
        '',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if cleaned != arch:
        view.write({'arch_db': cleaned})


def pre_init_hook(env):
    _strip_stale_currency_rate_xpath(env)
