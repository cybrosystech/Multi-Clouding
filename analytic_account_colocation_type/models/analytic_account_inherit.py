from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    analytic_account_type = fields.Selection(selection_add=[('co_location',
                                                             'Co Location')])


class AccountAssetInherit(models.Model):
    _inherit = 'account.asset'

    co_location = fields.Many2one('account.analytic.account',
                                  string="Co location",
                                  domain=[('analytic_account_type', '=',
                                           'co_location')],
                                  required=False)


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co location", domain=[(
            'analytic_account_type', '=', 'co_location')], required=False, )


class AccountAnalyticLineInherit(models.Model):
    _inherit = 'account.analytic.line'

    co_location_id = fields.Many2one("account.analytic.account",
                                     string="Co location",
                                     domain=[('analytic_account_type', '=',
                                              'co_location')], required=False,
                                     inverse='_set_co_location', store=True,
                                     readonly=False)

    def _set_co_location(self):
        _logger.info("Co location")


class PurchaseOrderLineCoLocation(models.Model):
    _inherit = 'purchase.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co Location", domain=[
            ('analytic_account_type', '=', 'co_location')], required=False, )


class SalesOrderLineInheritCoLocation(models.Model):
    _inherit = 'sale.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co Location", domain=[
            ('analytic_account_type', '=', 'co_location')], required=False, )
