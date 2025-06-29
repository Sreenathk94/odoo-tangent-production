{
    'name': 'HR Leave Widget',
    'version': '1.0',
    'category': 'Human Resources',
    'depends': ['hr_holidays', 'hr'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'hr_leave_widget/static/src/js/leave_type_widget.js',
            'hr_leave_widget/static/src/xml/leave_type_widget.xml',
        ],
    },
    'installable': True,
    'application': False,
}