{
    'name': 'HR Bonus Leave',
    'version': '1.0',
    'summary': 'Automatic allocation of annual bonus leave based on years of service',
    'description': """
        This module automatically allocates annual bonus leave to employees 
        based on their years of service in the organization.
        
        Features:
        - Calculates years of service based on employee's date of joining
        - Allocates bonus leave according to a predefined policy
        - Uses a scheduled cron job for annual allocation
        - Maintains allocation log to avoid duplicate allocations
    """,
    'category': 'Human Resources/Time Off',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr', 'hr_holidays'],
    'data': [
        'data/cron_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 