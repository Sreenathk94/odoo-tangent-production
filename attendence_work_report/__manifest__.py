{
    'name': 'Attendance Work Report',
    'version': '1.0',
    'depends': ['base', 'hr_attendance', 'hr','hr_timesheet'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/custom_hr_attendance.xml',
        'views/custom_hr_attendance_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
             'attendence_work_report/static/src/custom_attendace_report/custom_report.js',
             'attendence_work_report/static/src/custom_attendace_report/custom_report.xml',
             'attendence_work_report/static/src/custom_attendace_report/custom_report.scss',
        #
        ],
    },
    'installable': True,
    'application': False,
}
