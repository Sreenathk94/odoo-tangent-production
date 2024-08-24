{
    'name': 'TG Time Off',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'Summary': 'This module will manage  the leaves of employees',
    'description': 'This module helps to generate the leave report of employees ',
    'author': 'Fouvty',
    'maintainer': 'Fouvty',
    'website': '',
    'depends': ['base', 'hr', 'hr_holidays', 'tg_base', 'resource', 'tg_groups',
                ],
    'data': [
        'security/ir.model.access.csv',
        'views/tg_employee_views.xml',
        'views/tg_leave_form_view.xml',
        'views/tg_leave_report.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
