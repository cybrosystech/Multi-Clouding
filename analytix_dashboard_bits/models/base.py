from odoo import models, api, _
import pytz
import dateutil
import datetime
import logging

_logger = logging.getLogger(__name__)

class DashboardBaseBits(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """
            Helper method to collect important information about groupbys: raw
            field name, type, time information, qualified name, ...
        """
        split = gb.split(':')
        field = self._fields.get(split[0])
        if not field:
            raise ValueError("Invalid field %r on model %r" % (split[0], self._name))
        field_type = field.type
        gb_function = split[1] if len(split) == 2 else None
        temporal = field_type in ('date', 'datetime')
        tz_convert = field_type == 'datetime' and self._context.get('tz') in pytz.all_timezones
        qualified_field = self._field_to_sql(self._table, split[0], query)
        qualified_field = self.env.cr.mogrify(qualified_field).decode()
        if temporal:
            display_formats = {
                # Careful with week/year formats:
                #  - yyyy (lower) must always be used, *except* for week+year formats
                #  - YYYY (upper) must always be used for week+year format
                #         e.g. 2006-01-01 is W52 2005 in some locales (de_DE),
                #                         and W1 2006 for others
                #
                # Mixing both formats, e.g. 'MMM YYYY' would yield wrong results,
                # such as 2006-01-01 being formatted as "January 2005" in some locales.
                # Cfr: http://babel.pocoo.org/en/latest/dates.html#date-fields
                'hour': 'hh:00 dd MMM',
                'day': 'dd MMM yyyy', # yyyy = normal year
                'week': "'W'w YYYY",  # w YYYY = ISO week-year
                'month': 'MMMM yyyy',
                'quarter': 'QQQ yyyy',
                'year': 'yyyy',
            }
            time_intervals = {
                'hour': dateutil.relativedelta.relativedelta(hours=1),
                'day': dateutil.relativedelta.relativedelta(days=1),
                'week': datetime.timedelta(days=7),
                'month': dateutil.relativedelta.relativedelta(months=1),
                'quarter': dateutil.relativedelta.relativedelta(months=3),
                'year': dateutil.relativedelta.relativedelta(years=1)
            }
            if tz_convert:
                qualified_field = "timezone('%s', timezone('UTC',%s))" % (self._context.get('tz', 'UTC'), qualified_field)
            qualified_field = "date_trunc('%s', %s::timestamp)" % (gb_function or 'month', qualified_field)
        if field_type == 'boolean':
            qualified_field = "coalesce(%s,false)" % qualified_field
        return {
            'field': split[0],
            'groupby': gb,
            'type': field_type,
            'display_format': display_formats[gb_function or 'month'] if temporal else None,
            'interval': time_intervals[gb_function or 'month'] if temporal else None,
            'granularity': gb_function or 'month' if temporal else None,
            'tz_convert': tz_convert,
            'qualified_field': qualified_field,
        }

    def _read_group_prepare(self, orderby, aggregated_fields, annotated_groupbys, query):
        """
        Prepares the GROUP BY and ORDER BY terms for the read_group method. Adds the missing JOIN clause
        to the query if order should be computed against m2o field.

        :param orderby: the orderby definition in the form "%(field)s %(order)s"
        :param aggregated_fields: list of aggregated fields in the query
        :param annotated_groupbys: list of dictionaries returned by
            :meth:`_read_group_process_groupby`

            These dictionaries contain the qualified name of each groupby
            (fully qualified SQL name for the corresponding field),
            and the (non raw) field name.
        :param Query query: the query under construction
        :return: (groupby_terms, orderby_terms)
        """
        orderby_terms = []
        groupby_terms = [gb['qualified_field'] for gb in annotated_groupbys]
        if not orderby:
            return groupby_terms, orderby_terms

        self._check_qorder(orderby)

        # when a field is grouped as 'foo:bar', both orderby='foo' and
        # orderby='foo:bar' generate the clause 'ORDER BY "foo:bar"'
        groupby_fields = {
            gb[key]: gb['groupby']
            for gb in annotated_groupbys
            for key in ('field', 'groupby')
        }
        for order_part in orderby.split(','):
            order_split = order_part.split()  # potentially ["field:group_func", "desc"]
            order_field = order_split[0]
            is_many2one_id = order_field.endswith(".id")
            if is_many2one_id:
                order_field = order_field[:-3]
            if order_field == 'id' or order_field in groupby_fields:
                field = self._fields[order_field.split(':')[0]]
                if (
                    field.type == 'many2one'
                    and not self.env[field.comodel_name]._order == 'id'
                    and not is_many2one_id
                ):
                    order_clause = self._generate_order_by(order_part, query)
                    order_clause = order_clause.replace('ORDER BY ', '')
                    if order_clause:
                        orderby_terms.append(order_clause)
                        groupby_terms += [order_term.split()[0] for order_term in order_clause.split(',')]
                else:
                    order_split[0] = '"%s"' % groupby_fields.get(order_field, order_field)
                    orderby_terms.append(' '.join(order_split))
            elif order_field in aggregated_fields:
                order_split[0] = '"%s"' % order_field
                orderby_terms.append(' '.join(order_split))
            elif order_field not in self._fields:
                raise ValueError("Invalid field %r on model %r" % (order_field, self._name))
            elif order_field == 'sequence':
                pass
            else:
                # Cannot order by a field that will not appear in the results (needs to be grouped or aggregated)
                _logger.warning('%s: read_group order by `%s` ignored, cannot sort on empty columns (not grouped/aggregated)',
                             self._name, order_part)

        return groupby_terms, orderby_terms

    @api.model_create_multi
    def create(self, vals_list):
        res = super(DashboardBaseBits, self).create(vals_list)
        if 'ir.' not in self._name and self.env.user.has_group('base.group_user'):
            if self._name != 'dashboard.item.bits':
                dashboard_item_ids = self.env['dashboard.item.bits'].sudo().search([['model_id.model', '=', self._name]])
                if dashboard_item_ids:
                    dashboard_ids = dashboard_item_ids.mapped('bits_dashboard_id').ids
                    online_partner = self.env['res.users'].sudo().search([]).filtered(
                        lambda x: x.im_status in ['leave_online', 'online']).mapped("partner_id").ids
                    updates = [[(self._cr.dbname, 'res.partner', partner_id), 'model_update_notify',
                                {'type': 'NotifyUpdates', 'updates': {'dashboard_ids': dashboard_ids}}] for partner_id in
                            online_partner]
                    self.env['bus.bus']._sendmany(updates) 
        return res

    def write(self, vals):
        res = super(DashboardBaseBits, self).write(vals)
        for rec in self:
            if 'ir.' not in rec._name and self.env.user.has_group('base.group_user'):
                if rec._name == 'dashboard.item.bits':
                    online_partner = self.env['res.users'].sudo().search([]).filtered(
                        lambda x: x.im_status in ['leave_online', 'online']).mapped("partner_id").ids
                    updates = {'dashboard_ids': rec.bits_dashboard_id.ids, 'item_id': rec.id}
                    notification = [[(rec._cr.dbname, 'res.partner', partner_id), 'item_update_notify',
                                     {'type': 'NotifyUpdates', 'updates': updates}] for partner_id in online_partner]
                    self.env['bus.bus']._sendmany(notification)
                else:
                    dashboard_item_ids = self.env['dashboard.item.bits'].sudo().search(
                        [['model_id.model', '=', rec._name]])
                    if dashboard_item_ids:
                        dashboard_ids = dashboard_item_ids.mapped('bits_dashboard_id').ids
                        online_partner = self.env['res.users'].sudo().search([]).filtered(
                            lambda x: x.im_status in ['leave_online', 'online']).mapped("partner_id").ids
                        notification = [[(rec._cr.dbname, 'res.partner', partner_id), 'model_update_notify',
                                         {'type': 'NotifyUpdates', 'updates': {'dashboard_ids': dashboard_ids}}] for
                                        partner_id in
                                        online_partner]
                        self.env['bus.bus']._sendmany(notification)
        return res

    @api.model
    def _generate_order_by(self, order_spec, query):
        if self._context.get('skip_m2o'):
            return ""
        return super()._generate_order_by(order_spec, query)
