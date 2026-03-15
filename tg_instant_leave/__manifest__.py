{
    'name': 'Instant Leave Requests',
    'version': '17.0',
    'category': 'Human Resources',
    'summary': 'Track instant verbal leave requests and automate reminders',
    'description': """
        Allows HR to log instant leave calls from employees and automates email reminders
        if formal leave is not applied:
        - Day 3: Email to employee
        - Day 5: Email to manager
        - Day 8: Email to HR Manager
    """,
    'depends': ['hr', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences_data.xml',
        'views/instant_leave_views.xml',
        # 'views/res_users_views.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}