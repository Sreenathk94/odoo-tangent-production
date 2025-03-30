from odoo import models, fields, api
from odoo.exceptions import UserError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    is_leave_of_team_lead = fields.Boolean(
        string="Is leave of team Leader",
        compute='_compute_is_leave_of_team_lead',
        store=True
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
