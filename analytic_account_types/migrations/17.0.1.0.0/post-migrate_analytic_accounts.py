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
            'UPDATE account_analytic_account SET plan_id=%s where analytic_account_type=%s',
            [new_record.id, type[0]])

    cr.execute('UPDATE account_move_line AS am SET analytic_account_id = ('
               'SELECT jsonb_object_keys(analytic_distribution)::integer AS '
               'jsonb_keys FROM account_move_line ab WHERE ab.id = am.id)'
               ' WHERE EXISTS (SELECT 1 FROM account_move_line ab WHERE '
               'ab.id = am.id)')
    print("gggggggggg")
    _logger.info("Completed the post migration process")
