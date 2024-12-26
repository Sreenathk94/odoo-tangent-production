from odoo import api, fields, models


class HREmployee(models.Model):
    _inherit = "hr.employee"

    passport_expire = fields.Date(string="Passport Expire Date", copy=False)
    permit_expire = fields.Date(string="Labour Card Expire", copy=False)
    emergency_mobile = fields.Char(string="Emergency Mobile")
    is_hr_access = fields.Boolean(
        string="Has HR Access",
        compute="_compute_is_hr_access", readonly=True)

    @api.depends('user_id')
    def _compute_is_hr_access(self):
        for record in self:
            record.is_hr_access = self.env.user.has_group('tg_groups.group_employee_hr_details_access')


class HREmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    passport_expire = fields.Date(string="Passport Expire Date", copy=False)
    permit_expire = fields.Date(string="Labour Card Expire", copy=False)
    emergency_mobile = fields.Char(string="Emergency Mobile")
