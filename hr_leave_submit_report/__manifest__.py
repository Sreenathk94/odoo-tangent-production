{
    'name': 'Leave Submit Report',
    'version': '1.0',
    'depends': ['base', 'hr_attendance', 'hr', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'security/user_group.xml',
        'wizard/hr_leave_refuse_wizard_views.xml',
        'views/tg_leave_report.xml',
        'views/hr_leave_action_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_leave_submit_report/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
}
