from odoo import fields, models, api, _


class FavoriteFilterBits(models.Model):
    _name = 'favorite.filter.bits'
    _description = 'Favorite Filters'

    name = fields.Char('Name')
    dashboard_id = fields.Many2one('dashboard.bits', 'Dashboard')
    is_active = fields.Boolean('Active')
    filter_value = fields.Char('Filter Value')
    user_id = fields.Many2one('res.users','User')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(FavoriteFilterBits, self).create(vals_list)
        for record in records:
            if record.is_active:
                for rec in self.sudo().search(
                        [('id', 'not in', [record.id]), ('dashboard_id', '=', record.dashboard_id.id)]):
                    rec.is_active = False
        return records

    def write(self, vals):
        record = super(FavoriteFilterBits, self).write(vals)
        user_id = self.env.user.id
        if vals.get('is_active'):
            recs = self.sudo().search([('id', 'not in', self.ids), ('dashboard_id', 'in', self.dashboard_id.ids),('user_id','=',user_id)])
            for rec in recs:
                rec.is_active = False
        return record
