{
    'name': 'Tangent Attendance Timesheet',
    'version': '0.1',
    'Summary': 'Attendance Timesheet',
    'author': 'Fouvty',
    'description': 'Attendance Timesheet',
    'website': '',
    'category': 'hr_attendance',
    'data': [
        'security/ir.model.access.csv',
        'views/tg_attendance_view.xml',
        'views/tg_employee_view.xml',
        'views/tg_attendance_permission.xml',
    ],
    #Add Depends  sttl_timesheet_calendar
    'depends': ['base', 'hr', 'hr_attendance', 'tg_base', 'tg_groups'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
