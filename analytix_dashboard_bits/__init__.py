from . import models
from . import controllers 
from . import wizard

from odoo.api import SUPERUSER_ID

def uninstall_hook(env):
    dashboards = env['dashboard.bits'].search([])
    for dashboard in dashboards:
        if dashboard.dashboard_menu_id:
            dashboard.dashboard_menu_id.unlink()
