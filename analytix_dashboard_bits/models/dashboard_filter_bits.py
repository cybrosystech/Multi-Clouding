from odoo import models, fields, api, _


class DashboardFilterBits(models.Model):
    _name = "dashboard.filter.bits"
    _description = "Dashboard Filter"

    name = fields.Char(required=True)
    active = fields.Boolean('Active', default=True)
    model_id = fields.Many2one("ir.model", ondelete='cascade', required=True)
    field_id = fields.Many2one("ir.model.fields",
                               domain="[('model_id', '=', model_id),('ttype', 'in', ['selection','many2one','many2many', 'one2many'])]",
                               ondelete='cascade', required=True)
    dashboard_id = fields.Many2one("dashboard.bits")

    @api.onchange("model_id")
    def onchange_model_id(self):
        for rec in self.sudo():
            rec.field_id = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(DashboardFilterBits, self).create(vals_list)
        for record in records:
            online_partner = self.env['res.users'].sudo().search([]).filtered(
                lambda x: x.im_status in ['leave_online', 'online']).mapped(
                "partner_id").ids
            updates = {'dashboard_ids': [record.dashboard_id.id]}
            notification = [[(self._cr.dbname, 'res.partner', partner_id), 'ditem_create_notify',
                             {'type': 'NotifyUpdates', 'updates': updates}] for partner_id in online_partner]
            self.env['bus.bus']._sendmany(notification)
        return records
