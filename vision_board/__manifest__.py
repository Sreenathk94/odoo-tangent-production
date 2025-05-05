{
    'name': 'Vision Board',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Employee Dashboard and Privacy Policy',
    'description': """
        This module provides:
        * Employee Dashboard with attendance, leave, and project information
        * Privacy Policy Dashboard
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'hr',
        'hr_attendance',
        'hr_holidays',
        'hr_timesheet',
        'project',
    ],
    'data': [
        'views/vision_board_views.xml',
        'views/res_company_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'vision_board/static/src/js/*',
            'vision_board/static/src/xml/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}