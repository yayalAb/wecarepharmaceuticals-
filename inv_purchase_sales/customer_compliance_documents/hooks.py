# -*- coding: utf-8 -*-
import logging

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


def pre_init_hook(env):
    """
    Reactivate core partner form views.

    A previous cleanup deactivated Accounting/Purchase partner inherits that
    still mentioned stale field names. That removed
    property_supplier_payment_term_id and broke Purchase's xpath. Stale fields
    are handled by compatibility stubs on res.partner; views must stay active.
    """
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
            UPDATE ir_ui_view
               SET active = true
             WHERE model = 'res.partner'
               AND COALESCE(active, true) = false
               AND (
                    arch_db::text ILIKE '%%property_supplier_payment_term_id%%'
                 OR arch_db::text ILIKE '%%name=\\"accounting\\"%%'
                 OR name ILIKE '%%property.form.inherit%%'
                 OR name ILIKE '%%purchase.property%%'
               )
         RETURNING id, name
        """
    )
    extra = cr.fetchall()
    if extra:
        _logger.warning(
            'customer_compliance_documents: reactivated related partner views: %s',
            ', '.join(f'{vid}:{name}' for vid, name in extra),
        )


def post_init_hook(env):
    """Ensure core partner form views stay active after install."""
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
