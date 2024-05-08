import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # cr.execute('''
    #     UPDATE leasee_contract
    #     SET analytic_distribution =
    #         CASE
    #             WHEN project_site_id IS NOT NULL AND analytic_account_id IS NOT NULL THEN
    #                 CASE
    #                     WHEN analytic_distribution IS NULL THEN jsonb_build_object(
    #                         COALESCE(project_site_id::text, 'default'), '100',
    #                         COALESCE(analytic_account_id::text, 'default'), '100'
    #                     )
    #                     ELSE analytic_distribution || jsonb_build_object(
    #                         COALESCE(project_site_id::text, 'default'), '100',
    #                         COALESCE(analytic_account_id::text, 'default'), '100'
    #                     )
    #                 END
    #             WHEN project_site_id IS NOT NULL THEN
    #                 CASE
    #                     WHEN analytic_distribution IS NULL THEN jsonb_build_object(
    #                         COALESCE(project_site_id::text, 'default'), '100'
    #                     )
    #                     ELSE analytic_distribution || jsonb_build_object(
    #                         COALESCE(project_site_id::text, 'default'), '100'
    #                     )
    #                 END
    #             WHEN analytic_account_id IS NOT NULL THEN
    #                 CASE
    #                     WHEN analytic_distribution IS NULL THEN jsonb_build_object(
    #                         COALESCE(analytic_account_id::text, 'default'), '100'
    #                     )
    #                     ELSE analytic_distribution || jsonb_build_object(
    #                         COALESCE(analytic_account_id::text, 'default'), '100'
    #                     )
    #                 END
    #             ELSE analytic_distribution
    #         END
    # ''')
    _logger.info("Completed the post migration process")
