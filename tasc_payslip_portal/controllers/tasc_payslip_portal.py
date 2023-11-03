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
        print("dfghjgfhjgfhh", order_id)
        print("report_type", report_type)
        try:
            order_sudo = self._document_check_access('hr.payslip', order_id,
                                                     access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            print("ghjkhjkjhk")
            return self._show_report(model=order_sudo, report_type=report_type,
                                     report_ref='tasc_payslip_portal.action_report_payslip_portal',
                                     download=download)

        values = self._payslip_get_page_view_values(order_sudo, access_token,
                                                    **kw)
        values['message'] = message
        print("values", values)

        return request.render('tasc_payslip_portal.payslip_portal_template',
                              values)

    def _payslip_get_page_view_values(self, order, access_token, **kwargs):

        values = {
            'payslip': order,
            'token': access_token,
            # 'return_url': '/shop/payment/validate',
            'bootstrap_formatting': True,
            'employee_id': order.employee_id.id,
            'report_type': 'html',
            'action': order._get_portal_return_action(),
        }
        for line in order.line_ids:
            if line.category_id.name == 'Basic':
                values.update({'basic': line.amount if line.amount else 0.0})
            if line.category_id.name == 'Allowance':
                if 'allowance' in values:
                    amt = values.get('allowance')
                    amt = amt + line.amount
                    values.update({'allowance': amt})
                else:
                    values.update(
                        {'allowance': line.amount if line.amount else 0.0})
            if line.category_id.name == 'Deduction' and line.name == 'Provident Fund':
                if 'provident_fund' in values:
                    amt = values.get('provident_fund')
                    amt = amt + line.amount
                    values.update({'provident_fund': amt})
                else:
                    values.update(
                        {'provident_fund': line.amount if line.amount else 0.0})
        for input_line in order.input_line_ids:
            print("xcvbnmcvbn")
            if input_line.input_type_id.name == 'Other Benefits':
                values.update({
                                  'other_benefits': input_line.amount if input_line.amount else 0.0})
            else:
                values.update({'other_benefits': 0.0})
            if input_line.input_type_id.name == 'Other Deductions':
                values.update({
                                  'other_deduction': input_line.amount if input_line.amount else 0.0})
            else:
                values.update({'other_deduction': 0.0})

            if input_line.input_type_id.name == 'Bonus':
                values.update(
                    {'bonus': input_line.amount if input_line.amount else 0.0})
            else:
                values.update({'bonus': 0.0})
            if input_line.input_type_id.name == 'Loan':
                values.update(
                    {'loan': input_line.amount if input_line.amount else 0.0})
            else:
                values.update({'loan': 0.0})
            if input_line.input_type_id.name == 'Advance':
                values.update(
                    {
                        'advance': input_line.amount if input_line.amount else 0.0})
            else:
                values.update({'advance': 0.0})
            if input_line.input_type_id.name == 'Reimbursement':
                values.update(
                    {
                        'reimbursement': input_line.amount if input_line.amount else 0.0})
            else:
                values.update({'reimbursement': 0.0})

        return values

    @http.route(['/my/payslips', '/my/payslips/page/<int:page>'], type='http',
                auth="user", website=True)
    def portal_my_payslips(self, page=1, **kw):
        print("gggggggggggggggg")
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        print("partner", partner)
        PaySlip = request.env['hr.payslip']

        domain = self._prepare_payslip_domain(partner)

        searchbar_sortings = self._get_payslip_searchbar_sortings()
        print("searchbar_sortings", searchbar_sortings)
        # count for pager
        payslip_count = PaySlip.search_count(domain)
        print("payslip_count", payslip_count)
        # make pager
        pager = portal_pager(
            url="/my/payslips",
            # url_args={'sortby': sortby},
            total=payslip_count,
            page=page,
            step=self._items_per_page
        )
        print("domain", domain)
        # search the count to display, according to the pager data
        payslips = PaySlip.search(domain, limit=self._items_per_page,
                                  offset=pager['offset'])
        print("payslips", payslips)

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
            print("sdfghj")
            values['payslip_count'] = PaySlip.search_count(
                self._prepare_payslip_domain(partner)) \
                if PaySlip.check_access_rights('read',
                                               raise_exception=False) else 0

        return values

    def _prepare_payslip_domain(self, partner):
        print("partner", partner.name)
        print("user", partner.user_id)
        return [
            ('employee_id.address_home_id.id', '=', partner.id)
        ]

    def _get_payslip_searchbar_sortings(self):
        return {
            'name': {'label': _('Reference'), 'order': 'number'},
        }
