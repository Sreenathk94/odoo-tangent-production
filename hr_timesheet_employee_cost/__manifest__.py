{
    'name': 'Timesheet Employee Cost',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Add employee cost calculations to timesheet reports and views',
    'description': """
        - Adds employee_cost field to hr.employee.
        - Computes employee cost in timesheet analysis and task reports.
        - Updates pivots/graphs with employee cost measure.
        - Adds employee cost column to PDF timesheet reports.
        - Fixes invalid field errors (billable_time, non_billable_time).
    """,
    'author': 'Your Name',
    'website': 'https://example.com',
    'depends': ['hr_timesheet', 'project', 'hr', 'account',
                'hr_hourly_cost', 'sttl_timesheet_calendar'],  # ADDED:
    # 'account' for model_account_analytic_line
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_employee_cost_import_wizard.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_cost_views.xml',
        'views/hr_employee_cost_menu.xml',
        'report/project_report_view.xml',
        'report/report_timesheet_templates.xml',
        'report/hr_timesheet_report_view.xml',
    ],
    'external_dependencies': {
            'python': [
                'openpyxl',
            ],
        },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}