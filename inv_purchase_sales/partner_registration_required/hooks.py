# -*- coding: utf-8 -*-
import json
import logging
import os
import re

_logger = logging.getLogger(__name__)

_REPLACEMENTS = (
    (
        re.compile(r"""invisible\s*=\s*["']not\s+duplicate_bank_partner_ids["']"""),
        'invisible="duplicated_bank_account_partners_count == 0"',
    ),
    (
        re.compile(r"""invisible\s*=\s*["']duplicate_bank_partner_ids["']"""),
        'invisible="duplicated_bank_account_partners_count"',
    ),
    (
        re.compile(
            r"""<field\s+[^>]*name\s*=\s*["']duplicate_bank_partner_ids["'][^/]*/>"""
        ),
        '',
    ),
    (
        re.compile(
            r"""<field\s+[^>]*name\s*=\s*["']duplicate_bank_partner_ids["'][^>]*>.*?</field>""",
            re.DOTALL,
        ),
        '',
    ),
)


def _rewrite_xml(xml):
    if not isinstance(xml, str) or 'duplicate_bank_partner_ids' not in xml:
        return xml, False
    new_xml = xml
    for pattern, repl in _REPLACEMENTS:
        new_xml = pattern.sub(repl, new_xml)
    if 'duplicate_bank_partner_ids' in new_xml:
        new_xml = new_xml.replace(
            'duplicate_bank_partner_ids',
            'duplicated_bank_account_partners_count',
        )
    return new_xml, new_xml != xml


def _fix_partner_views(env):
    cr = env.cr
    cr.execute(
        """
            SELECT id, name, arch_db
              FROM ir_ui_view
             WHERE model = 'res.partner'
               AND arch_db::text ILIKE '%%duplicate_bank_partner_ids%%'
        """
    )
    for view_id, name, arch_json in cr.fetchall():
        if arch_json is None:
            continue
        changed = False
        if isinstance(arch_json, str):
            new_xml, changed = _rewrite_xml(arch_json)
            payload = json.dumps(new_xml) if changed else None
        elif isinstance(arch_json, dict):
            out = {}
            for lang, xml in arch_json.items():
                new_xml, did = _rewrite_xml(xml)
                out[lang] = new_xml
                changed = changed or did
            payload = json.dumps(out) if changed else None
        else:
            payload = None
        if not payload:
            continue
        cr.execute(
            """
                UPDATE ir_ui_view
                   SET arch_db = %s::jsonb
                 WHERE id = %s
            """,
            (payload, view_id),
        )
        _logger.warning(
            'partner_registration_required: fixed stale bank field in view %s (%s)',
            view_id,
            name,
        )


def _deactivate_views_from_missing_modules(env):
    """Deactivate views owned by modules marked installed but missing on disk."""
    cr = env.cr
    addons_paths = []
    try:
        import odoo.addons as addons_pkg
        for path in getattr(addons_pkg, '__path__', []):
            addons_paths.append(path)
    except Exception:
        pass
    # Also use configured addons path from tools.config if available
    try:
        from odoo.tools import config
        for path in (config.get('addons_path') or '').split(','):
            path = path.strip()
            if path:
                addons_paths.append(path)
    except Exception:
        pass

    cr.execute("SELECT name FROM ir_module_module WHERE state = 'installed'")
    installed = [row[0] for row in cr.fetchall()]
    missing = []
    for name in installed:
        if name in ('base', 'web'):
            continue
        if any(os.path.isdir(os.path.join(root, name)) for root in addons_paths):
            continue
        missing.append(name)

    if not missing:
        return

    _logger.warning(
        'partner_registration_required: modules installed but missing on disk: %s',
        ', '.join(missing),
    )
    cr.execute(
        """
            UPDATE ir_ui_view AS v
               SET active = false
              FROM ir_model_data AS d
             WHERE d.model = 'ir.ui.view'
               AND d.res_id = v.id
               AND d.module = ANY(%s)
               AND COALESCE(v.active, true) = true
         RETURNING d.module, v.id, v.name
        """,
        (missing,),
    )
    for module, view_id, name in cr.fetchall():
        _logger.warning(
            'Deactivated view %s (%s) from missing module %s',
            view_id,
            name,
            module,
        )

    cr.execute(
        """
            UPDATE ir_module_module
               SET state = 'uninstalled'
             WHERE name = ANY(%s)
               AND state = 'installed'
        """,
        (missing,),
    )


def post_init_hook(env):
    _fix_partner_views(env)
    _deactivate_views_from_missing_modules(env)
