from collections import defaultdict
from odoo import _, models
from odoo.exceptions import UserError

def _prepare_data(env, docids, data):

    layout_wizard = env['product.label.layout'].browse(data.get('layout_wizard'))
    if data.get('active_model') == 'product.template':
        Product = env['product.template'].with_context(display_default_code=False)
    elif data.get('active_model') == 'product.product':
        Product = env['product.product'].with_context(display_default_code=False)
    elif data.get("studio") and docids:
        products = env['product.template'].with_context(display_default_code=False).browse(docids)
        quantity_by_product = defaultdict(list)
        for product in products:
            quantity_by_product[product].append((product.barcode, 1))
        return {
            'quantity': quantity_by_product,
            'page_numbers': 1,
            'pricelist': layout_wizard.pricelist_id,
        }
    else:
        raise UserError(_('Product model not defined, Please contact your administrator.'))

    if not layout_wizard:
        return {}

    total = 0
    qty_by_product_in = data.get('quantity_by_product')
    products = Product.search([('id', 'in', [int(p) for p in qty_by_product_in.keys()])], order='name desc')
    quantity_by_product = defaultdict(list)
    for product in products:
        q = qty_by_product_in[str(product.id)]
        quantity_by_product[product].append((product.barcode, q))
        total += q
    if data.get('custom_barcodes'):
        for product, barcodes_qtys in data.get('custom_barcodes').items():
            quantity_by_product[Product.browse(int(product))] += (barcodes_qtys)
            total += sum(qty for _, qty in barcodes_qtys)

    return {
        'quantity': quantity_by_product,
        'page_numbers': (total - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
        'price_included': data.get('price_included'),
        'extra_html': layout_wizard.extra_html,
        'pricelist': layout_wizard.pricelist_id,
    }

class ReportProductTemplateLabelDymo(models.AbstractModel):
    _name = 'report.analytic_account_types.report_label_custom'
    _description = 'Custom Product Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)