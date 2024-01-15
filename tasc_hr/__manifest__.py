{
    'name': 'Hr Custom',
    'summary': """ The app has feature to add some fields to hr contract. """,
    'description': """The app has feature to add some fields to hr contract""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'category': 'Human Resources/Contracts',
    'version': '14.0.1.0.0',
    'depends': ['hr','hr_contract'],
    'data':
        [
            'security/ir.model.access.csv',
            'views/hr_contract_view.xml',
            'views/hr_employee_views.xml',
            'views/hr_sub_department_views.xml',
        ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
