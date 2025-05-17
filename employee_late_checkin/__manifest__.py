{
    'name': 'Employee Late Check-in Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'depends': ['hr_attendance'],
    'data': [
        'views/late_checkin_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'employee_late_checkin/static/src/js/late_checkin_dashboard.js',
            'employee_late_checkin/static/src/templates/late_checkin_template.xml',
        ],
    },
    'installable': True,
    'application': True,
}