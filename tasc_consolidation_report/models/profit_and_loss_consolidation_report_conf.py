from odoo import models, fields, api


class ProfitLossReportConsolidationConfig(models.Model):
    _name = 'consolidation.report.config'
    _description = 'consolidation report configuration'
    _rec_name = 'name'

    name = fields.Char()
    active_bool = fields.Boolean('active')
    profit_loss_related_ids = fields.One2many('consolidation.config.relation',
                                              'profit_loss_config_id')
    config_type = fields.Selection(selection=[('profit_loss', 'Profit And Loss')
        , ('balance_sheet', 'Balance Sheet')])


class ProfitLossConsolidationRelation(models.Model):
    _name = 'consolidation.config.relation'
    _order = 'sequence, id'

    consolidation_parent_group_id = fields.Many2one('consolidation.group',
                                                    domain=[('parent_id', '=',
                                                             False)])
    consolidation_child_group_ids = fields.Many2many('consolidation.group')
    profit_loss_config_id = fields.Many2one('consolidation.report.config')
    line_type = fields.Selection(selection=[('main_lines', 'Main lines'),
                                            ('total_config', 'Total Config')],
                                 default='main_lines')
    consolidation_parent = fields.Many2many('consolidation.group',
                                            'consolidation_report_rel',
                                            domain=[('parent_id', '=',
                                                     False)])
    config_name = fields.Char()
    sequence = fields.Integer(string='Sequence', required=True,)

    @api.onchange('consolidation_parent_group_id')
    def onchange_parent_group_consolidation(self):
        """On adding/changing the parent group child ids will be updated in
        consolidation_child_group_ids field"""
        if self.consolidation_parent_group_id:
            self.consolidation_child_group_ids = \
                self.consolidation_parent_group_id.child_ids.ids
