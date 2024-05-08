import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    analytic_account_types = [
        ('cost_center', 'Cost Center'), ('project_site', 'Project/Site'),
        ('type', 'Type'), ('location', 'Location'),
        ('co_location', 'Co Location')]
    plan = env['account.analytic.plan']
    plan_ids = []
    for type in analytic_account_types:
        new_record = plan.create({
            'name': type[1],
        })
        print("new_record", new_record.name)
        plan_ids.append(new_record.id)
        cr.execute(
            'UPDATE account_analytic_account SET plan_id=%s,root_plan_id=%s where analytic_account_type=%s',
            [new_record.id, new_record.id, type[0]])

    cr.execute('UPDATE account_move_line AS am '
               'SET analytic_account_id = ('
               'SELECT jsonb_object_keys(analytic_distribution)::integer AS jsonb_keys '
               'FROM account_move_line ab '
               'WHERE ab.id = am.id '
               'AND ('
               ' SELECT COUNT(*) FROM jsonb_object_keys(ab.analytic_distribution)'
               ') = 1'
               'LIMIT 1'
               ')'
               'WHERE EXISTS ('
               'SELECT 1 FROM account_move_line ab '
               'WHERE ab.id = am.id'
               ')'
               'AND analytic_account_id IS NULL')
    print("gggggggggg")
    cr.execute('''
        UPDATE account_move_line
        SET analytic_distribution =
            CASE
                WHEN project_site_id IS NOT NULL THEN
                    CASE
                        WHEN analytic_distribution IS NULL THEN jsonb_build_object(
                            COALESCE(project_site_id::text, 'default'), '100'
                        )
                        ELSE analytic_distribution || jsonb_build_object(
                            COALESCE(project_site_id::text, 'default'), '100'
                        )
                    END
                ELSE analytic_distribution
            END
    ''')


    #
    # cr.execute('UPDATE account_asset AS am '
    #            'SET analytic_account_id = ('
    #            'SELECT jsonb_object_keys(analytic_distribution)::integer AS jsonb_keys '
    #            'FROM account_asset ab '
    #            'WHERE ab.id = am.id '
    #            'AND ('
    #            ' SELECT COUNT(*) FROM jsonb_object_keys(ab.analytic_distribution)'
    #            ') = 1'
    #            'LIMIT 1'
    #            ')'
    #            'WHERE EXISTS ('
    #            'SELECT 1 FROM account_asset ab '
    #            'WHERE ab.id = am.id'
    #            ')'
    #            'AND analytic_account_id IS NULL')
    # print("gggggggggg")
    # cr.execute('''
    #      UPDATE account_asset
    #      SET analytic_distribution =
    #          CASE
    #              WHEN project_site_id IS NOT NULL THEN
    #                  CASE
    #                      WHEN analytic_distribution IS NULL THEN jsonb_build_object(
    #                          COALESCE(project_site_id::text, 'default'), '100'
    #                      )
    #                      ELSE analytic_distribution || jsonb_build_object(
    #                          COALESCE(project_site_id::text, 'default'), '100'
    #                      )
    #                  END
    #              ELSE analytic_distribution
    #          END
    #  ''')
    _logger.info("Completed the post migration process")
