from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    privacy_policy_pdf = fields.Binary(string='Privacy Policy PDF', attachment=True)
    privacy_policy_filename = fields.Char(string='Privacy Policy Filename')
    privacy_policy_last_updated = fields.Datetime(string='Last Updated', default=fields.Datetime.now)
    privacy_policy_content = fields.Html(string='Privacy Policy Content', sanitize=True)

    daily_work_hour_dashboard = fields.Float(
        string='Daily Work Hours',
        default=9.0,
        help='Default daily work hours to be displayed in the employee dashboard'
    )

    monthly_working_days = fields.Integer(
        string='Monthly Working Days',
        default=22,
        help='Default number of working days in a month for the employee dashboard'
    )
