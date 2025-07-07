from odoo import models,fields
from odoo.addons.product.wizard.product_label_layout import ProductLabelLayout


def _prepare_report_data(self):
    if self.custom_quantity <= 0:
        raise UserError(_('You need to set a positive quantity.'))

    # Get layout grid
    if self.print_format == 'dymo':
        xml_id = 'product.report_product_template_label_dymo'
    elif self.print_format == 'custom':
        xml_id = 'analytic_account_types.report_product_template_label_custom'
    elif 'x' in self.print_format:
        xml_id = 'product.report_product_template_label_%sx%s' % (self.columns, self.rows)
        if 'xprice' not in self.print_format:
            xml_id += '_noprice'
    else:
        xml_id = ''

    active_model = ''
    if self.product_tmpl_ids:
        products = self.product_tmpl_ids.ids
        active_model = 'product.template'
    elif self.product_ids:
        products = self.product_ids.ids
        active_model = 'product.product'
    else:
        raise UserError(_("No product to print, if the product is archived please unarchive it before printing its label."))

    # Build data to pass to the report
    data = {
        'active_model': active_model,
        'quantity_by_product': {p: self.custom_quantity for p in products},
        'layout_wizard': self.id,
        'price_included': 'xprice' in self.print_format,
    }
    return xml_id, data

ProductLabelLayout._prepare_report_data = _prepare_report_data

class ProductLabelLayoutInherit(models.TransientModel):
    _inherit = 'product.label.layout'

    print_format = fields.Selection(selection_add=[
        ('custom', 'Custom Label'),
    ], ondelete={'custom': 'set default'})

