{
    'name': 'Attendance Work Report',
    'version': '1.0',
    'depends': ['base','hr_attendance','hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/attendance_custom_views.xml',

    ],
    'installable': True,
    'application': False,
}
