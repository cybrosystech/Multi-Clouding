{
    'name': 'Select All companies',
    'summary': """""",

    'description': """""",

    'author': "",
    'website': "",
    'category': '',
    'version': '17.0.1.0.0',
    'depends': ['web', 'base'],

    'data':
        [
            # 'views/assets.xml',
        ],
    # 'qweb': [
    #     'static/src/xml/company_base_menuswitch.xml',
    # ],
    'assets': {
        'web.assets_backend': [
            'company_click_custom/static/src/js/switch_company_all.js',
            'company_click_custom/static/src/xml/company_base_menuswitch.xml'
        ], }
}
