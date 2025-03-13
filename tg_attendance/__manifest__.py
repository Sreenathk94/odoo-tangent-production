{
    'name': 'Tangent Attendance Timesheet',
    'version': '17.0.1.0.6',
    'Summary': 'Attendance Timesheet',
    'author': 'Fouvty',
    'description': 'Attendance Timesheet',
    'website': '',
    'category': 'hr_attendance',
    'data': [
        'security/ir.model.access.csv',
        'views/res_company.xml',
        'views/tg_attendance_view.xml',
        'views/tg_employee_view.xml',
        'views/tg_attendance_permission.xml',
        'views/website_attendance_template.xml',
        'views/attendance_clail_approval.xml',
    ],
     'assets': {
        'web.assets_frontend': [
            '/tg_attendance/static/src/attendance_claim.js'
        ]
    },
    #Add Depends  sttl_timesheet_calendar
    'depends': ['base','website', 'hr', 'hr_attendance', 'tg_base', 'tg_groups'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
