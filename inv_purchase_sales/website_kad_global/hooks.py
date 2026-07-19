# -*- coding: utf-8 -*-
def _unlock_homepage_noupdate(env):
    """Allow homepage XML to refresh on every module upgrade."""
    env['ir.model.data'].search([
        ('module', '=', 'website_kad_global'),
        ('name', '=', 'page_home'),
    ]).write({'noupdate': False})


def post_init_hook(env):
    _unlock_homepage_noupdate(env)


def uninstall_hook(env):
    pass
