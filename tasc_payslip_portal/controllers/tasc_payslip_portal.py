from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, \
    pager as portal_pager, get_records_pager


class PayslipPortal(CustomerPortal):

    @http.route(['/my/payslips/<int:order_id>'], type='http', auth="public",
                website=True)
    def payslip_portal_order_page(self, order_id, report_type=None,
                                  access_token=None,
                                  message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access('hr.payslip', order_id,
                                                     access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type,
                                     report_ref='tasc_payslip_portal.action_report_payslip_portal',
                                     download=download)

        values = self._payslip_get_page_view_values(order_sudo, access_token,
                                                    **kw)
        values['message'] = message
        return request.render('tasc_payslip_portal.payslip_portal_template',
                              values)

    def _payslip_get_page_view_values(self, order, access_token, **kwargs):

        values = {
            'payslip': order,
            'token': access_token,
            'bootstrap_formatting': True,
            'employee_id': order.employee_id.id,
            'report_type': 'html',
            'action': order._get_portal_return_action(),
        }
        values.update(
            {'basic': 0.0,
             'net_salary': 0.0,
             'other_benefits': 0.0,
             'bonus': 0.0,
             'allowance': 0.0,
             'loan': 0.0,
             'advance': 0.0,
             'other_deduction': 0.0,
             'reimbursement': 0.0,
             'provident_fund': 0.0
             }
        )
        for line in order.line_ids:
            if line.category_id.name == 'Basic':
                if 'basic' in values:
                    amt = values.get('basic')
                    amt = amt + line.amount
                    values.update({'basic': amt if amt else 0.0})
                else:
                    values.update(
                        {'basic': line.amount if line.amount else 0.0})

            if line.category_id.name == 'Net':
                if 'net_salary' in values:
                    amt = values.get('net_salary')
                    amt = amt + line.amount
                    values.update({'net_salary': amt if amt else 0.0})
                else:
                    values.update(
                        {'net_salary': line.amount if line.amount else 0.0})

            if line.name == 'Other Benefits':
                if 'other_benefits' in values:
                    amt = values.get('other_benefits')
                    amt = amt + line.amount
                    values.update({'other_benefits': amt if amt else 0.0})
                else:
                    values.update(
                        {'other_benefits': line.amount if line.amount else 0.0})

            if line.name == 'Bonus':
                if 'bonus' in values:
                    amt = values.get('bonus')
                    amt = amt + line.amount
                    values.update({'bonus': amt if amt else 0.0})
                else:
                    values.update(
                        {'bonus': line.amount if line.amount else 0.0})

            if line.category_id.name == 'Allowance':
                if 'allowance' in values:
                    amt = values.get('allowance')
                    amt = amt + line.amount
                    values.update({'allowance': amt if amt else 0.0})
                else:
                    values.update(
                        {'allowance': line.amount if line.amount else 0.0})

            if line.name == 'Loan':
                if 'loan' in values:
                    amt = values.get('loan')
                    amt = amt + line.amount
                    values.update({'loan': amt if amt else 0.0})
                else:
                    values.update(
                        {'loan': line.amount if line.amount else 0.0})

            if line.name == 'Advance':
                if 'advance' in values:
                    amt = values.get('advance')
                    amt = amt + line.amount
                    values.update({'advance': amt if amt else 0.0})
                else:
                    values.update(
                        {'advance': line.amount if line.amount else 0.0})

            if line.name == 'Other Deductions':
                if 'other_deduction' in values:
                    amt = values.get('other_deduction')
                    amt = amt + line.amount
                    values.update({'other_deduction': amt if amt else 0.0})
                else:
                    values.update(
                        {
                            'other_deduction': line.amount if line.amount else 0.0})

            if line.name == 'Reimbursement':
                if 'reimbursement' in values:
                    amt = values.get('reimbursement')
                    amt = amt + line.amount
                    values.update({'reimbursement': amt if amt else 0.0})
                else:
                    values.update(
                        {
                            'reimbursement': line.amount if line.amount else 0.0})

            if line.category_id.name == 'Deduction' and line.name == 'Provident Fund':
                if 'provident_fund' in values:
                    amt = values.get('provident_fund')
                    amt = amt + line.amount
                    values.update({'provident_fund': amt if amt else 0.0})
                else:
                    values.update(
                        {'provident_fund': line.amount if line.amount else 0.0})

        return values

    @http.route(['/my/payslips', '/my/payslips/page/<int:page>'], type='http',
                auth="user", website=True)
    def portal_my_payslips(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PaySlip = request.env['hr.payslip']
        domain = self._prepare_payslip_domain(partner)

        searchbar_sortings = self._get_payslip_searchbar_sortings()
        # count for pager
        payslip_count = PaySlip.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/payslips",
            total=payslip_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        payslips = PaySlip.search(domain, limit=self._items_per_page,
                                  offset=pager['offset'])
        values.update({
            'payslips': payslips.sudo(),
            'page_name': 'payslip',
            'pager': pager,
            'default_url': '/my/payslips',
        })
        return request.render("tasc_payslip_portal.portal_my_payslip", values)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        PaySlip = request.env['hr.payslip']
        if 'payslip_count' in counters:
            values['payslip_count'] = PaySlip.search_count(
                self._prepare_payslip_domain(partner)) \
                if PaySlip.check_access_rights('read',
                                               raise_exception=False) else 0
        return values

    def _prepare_payslip_domain(self, partner):
        return [
            ('employee_id.address_home_id.id', '=', partner.id)
        ]

    def _get_payslip_searchbar_sortings(self):
        return {
            'name': {'label': _('Reference'), 'order': 'number'},
        }
