from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import float_round



class HrLeave(models.Model):
    _inherit = 'hr.leave'

    is_leave_of_team_lead = fields.Boolean(
        string="Is leave of team Leader",
        compute='_compute_is_leave_of_team_lead',
        store=True
    )
    duration_days_only = fields.Float(
        string='Requested (Days Only)',
        compute='_compute_duration_days_only',
        help="Displays the duration of the leave request strictly in days."
    )

    @api.depends('employee_ids')
    def _compute_is_leave_of_team_lead(self):
        """Compute if the leave belongs to a team leader."""
        for rec in self:
            user = self.env.user
            officer_group = self.env.ref('your_module.group_hr_holidays_user',
                                         raise_if_not_found=False)
            admin_group = self.env.ref('your_module.group_hr_holidays_manager',
                                       raise_if_not_found=False)

            if admin_group and admin_group in user.groups_id:
                rec.is_leave_of_team_lead = False
            elif officer_group and officer_group in user.groups_id:
                rec.is_leave_of_team_lead = user.employee_id in rec.employee_ids
            else:
                rec.is_leave_of_team_lead = False

    def action_approve(self, check_state=True):
        """Override approve method to restrict team leads from approving their own leave."""
        for leave in self:
            user = self.env.user
            officer_group = self.env.ref('hr_holidays.group_hr_holidays_user',
                                         raise_if_not_found=False)
            admin_group = self.env.ref('hr_holidays.group_hr_holidays_manager',
                                       raise_if_not_found=False)

            # Admins can approve without restriction
            if admin_group and admin_group in user.groups_id:
                continue

            # Team leads cannot approve their own leave
            if officer_group and officer_group in user.groups_id and user.employee_id in leave.employee_ids:
                raise UserError("Team leads cannot approve their own leave request.")

        return super(HrLeave, self).action_approve(check_state)

    @api.constrains('holiday_status_id', 'date_from')
    def _check_probation_period(self):
        for record in self:
            if not record.employee_id or not record.date_from or not record.holiday_status_id:
                continue
            # Check only for Annual Leave
            if record.holiday_status_id.code in ['AL', 'SL']:
                # Use contract start date (if defined) or fallback to employee join date
                joining_date = record.employee_id.date_of_join
                if not joining_date:
                    raise UserError("Missing joining date")
                if record.date_from.date() < joining_date + timedelta(days=180):
                    raise UserError("Annual leave /Sick Leave are not allowed during the probation period (first 6 months).")

    @api.depends('number_of_days_display', 'number_of_hours_display','leave_type_request_unit')
    def _compute_duration_days_only(self):
        for record in self:
            if record.leave_type_request_unit == 'hour':
                record.duration_days_only = float_round(record.number_of_hours_display / 9.0,
                                                        precision_digits=2)  # assuming 9 hours = 1 day
            else:
                record.duration_days_only = float_round(record.number_of_days_display, precision_digits=2)
