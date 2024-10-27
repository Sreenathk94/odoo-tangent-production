{
    'name': 'Leave Submit Report',
    'version': '1.0',
    'depends': ['base','hr_attendance','hr','hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/tg_leave_report.xml',
    ],
    'installable': True,
    'application': False,
}
