import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute('update account_analytic_line set x_plan137_id=x_plan134_id where x_plan134_id is not NULL')
    cr.execute('update account_analytic_line set x_plan134_id=NULL where x_plan134_id is not NULL')

    cr.execute('update account_analytic_line set x_plan138_id=project_site_id where project_site_id is not NULL')
    cr.execute('update account_analytic_line set project_site_id=NULL where project_site_id is not NULL')

    cr.execute('update account_analytic_line set x_plan138_id=account_id where account_id is not NULL')
    cr.execute('update account_analytic_line set account_id=NULL where account_id is not NULL')

    cr.execute('update account_analytic_line set x_plan139_id=type_id where type_id is not NULL')
    cr.execute('update account_analytic_line set type_id=NULL where type_id is not NULL')

    cr.execute('update account_analytic_line set x_plan140_id=location_id where location_id is not NULL')
    cr.execute('update account_analytic_line set location_id=NULL where location_id is not NULL')

    cr.execute('update account_analytic_line set x_plan141_id=co_location_id where co_location_id is not NULL')
    cr.execute('update account_analytic_line set co_location_id=NULL where co_location_id is not NULL')

    _logger.info("Completed the post migration process")
