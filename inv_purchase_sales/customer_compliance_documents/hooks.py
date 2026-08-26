# -*- coding: utf-8 -*-
import json
import logging
import re

_logger = logging.getLogger(__name__)

_CORE_PARTNER_VIEW_MODULES = (
    'base',
    'account',
    'purchase',
    'sale',
    'sale_management',
    'account_peppol',
    'contacts',
)

# Replace fragile xpath on property_supplier_payment_term_id with a stable group inject.
_PURCHASE_BUYER_BLOCK_RE = re.compile(
    r'<field\s+name="property_supplier_payment_term_id"\s+position="before"\s*>'
    r'(.*?)</field>',
    re.DOTALL,
)
_PURCHASE_BUYER_BLOCK_REPL = (
    r'<group name="purchase" position="inside">\1</group>'
)


def _arch_as_dict(arch_json):
    if arch_json is None:
        return None
    if isinstance(arch_json, dict):
        return dict(arch_json)
    if isinstance(arch_json, str):
        return {'en_US': arch_json}
    return None


def pre_init_hook(env):
    """Repair partner form views so Compliance Documents tab can be installed."""
    cr = env.cr

    cr.execute(
        """
            UPDATE ir_ui_view AS v
               SET active = true
              FROM ir_model_data AS d
             WHERE d.model = 'ir.ui.view'
               AND d.res_id = v.id
               AND d.module = ANY(%s)
               AND v.model = 'res.partner'
               AND COALESCE(v.active, true) = false
         RETURNING v.id, v.name, d.module
        """,
        (list(_CORE_PARTNER_VIEW_MODULES),),
    )
    reactivated = cr.fetchall()
    if reactivated:
        _logger.warning(
            'customer_compliance_documents: reactivated partner views: %s',
            ', '.join(f'{module}:{vid}:{name}' for vid, name, module in reactivated),
        )

    cr.execute(
        """
            SELECT v.id, v.name, v.arch_db
              FROM ir_ui_view v
              JOIN ir_model_data d
                ON d.model = 'ir.ui.view' AND d.res_id = v.id
             WHERE d.module = 'purchase'
               AND d.name = 'view_partner_property_form'
        """
    )
    row = cr.fetchone()
    if not row:
        return

    view_id, name, arch_json = row
    arch_map = _arch_as_dict(arch_json)
    if not arch_map:
        return

    changed = False
    out = {}
    for lang, xml in arch_map.items():
        if isinstance(xml, str) and _PURCHASE_BUYER_BLOCK_RE.search(xml):
            out[lang] = _PURCHASE_BUYER_BLOCK_RE.sub(_PURCHASE_BUYER_BLOCK_REPL, xml, count=1)
            changed = True
        else:
            out[lang] = xml

    if changed:
        cr.execute(
            """
                UPDATE ir_ui_view
                   SET arch_db = %s::jsonb
                 WHERE id = %s
            """,
            (json.dumps(out), view_id),
        )
        _logger.warning(
            'customer_compliance_documents: patched purchase partner view %s (%s)',
            view_id,
            name,
        )


def post_init_hook(env):
    """Keep core partner form views active after install/upgrade."""
    View = env['ir.ui.view'].sudo()
    Data = env['ir.model.data'].sudo()
    data_rows = Data.search([
        ('model', '=', 'ir.ui.view'),
        ('module', 'in', list(_CORE_PARTNER_VIEW_MODULES)),
    ])
    views = View.browse(data_rows.mapped('res_id')).exists().filtered(
        lambda v: v.model == 'res.partner' and not v.active
    )
    if views:
        _logger.warning(
            'customer_compliance_documents post_init: reactivating %s',
            views.mapped('name'),
        )
        views.write({'active': True})
