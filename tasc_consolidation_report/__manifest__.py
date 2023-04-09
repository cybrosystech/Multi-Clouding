{
    'name': 'Tasc Consolidation Report',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['account_consolidation'],

    'data':
        [
            'security/ir.model.access.csv',
            'views/profit_and_loss_consolidation_config_view.xml',
            'wizard/consolidation_report_wizard_view.xml',
        ],

    'qweb': [],
}
