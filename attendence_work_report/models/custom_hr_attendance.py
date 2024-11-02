from odoo import api, models, fields


class HrAttendance(models.Model):
    _name = 'custom.hr.attendance'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Employee")

    custom_report_based_on = fields.Selection([('today', 'Filter by Today'),
                                               ('week', 'Filter by Week'),
                                               ('month', 'Filter by Month'),
                                               ('custom',
                                                'Filter by Custom Date')],
                                              default='today',
                                              string="Custom report based on")

    custom_total_hours = fields.Float(string="Custom total hours",
                                      compute='_compute_custom_total_hours')

    @api.depends('custom_report_based_on')
    def _compute_custom_total_hours(self):
        """This function is used to compute the custom total hours based on the
        report"""
        for rec in self:
            rec.custom_total_hours = False
            if rec.custom_report_based_on == 'today':
                rec.custom_total_hours = rec.worked_hours

