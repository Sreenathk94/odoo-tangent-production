# models/hr_leave_allocation.py
from odoo import api, models, fields


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    is_probation_accrual = fields.Boolean("Probation Leave Accrual")
    is_post_probation_allocation = fields.Boolean("Post-Probation Leave Allocation")
    is_annual_allocation = fields.Boolean(string="Annual Leave Allocation")
    leave_mode = fields.Selection([
        ('paid', 'Paid Leave'),
        ('compensatory', 'Compensatory Days'),
    ], string="Leave Mode", default='compensatory')
    state = fields.Selection(selection_add=[('paid', 'Paid Leave Confirmed')])
    is_cp_leave = fields.Boolean("Is Compensatory Allocation", default=False)

    @api.onchange('holiday_status_id')
    def compute_is_cp_leave(self):
        for rec in self:
            rec.is_cp_leave = rec.holiday_status_id.code == 'CP'

    def action_validate(self):
        for record in self:
            if record.holiday_status_id.code == 'CP':
                if record.leave_mode == 'paid':
                    # Custom state transition or logic for paid leave
                    record.write({'state': 'paid'})
                    return  # skip normal process
        return super().action_validate()

    def action_refuse(self):
        for record in self:
            if record.state == 'paid':
                record.write({'state': 'refuse'})
                return
        return super().action_validate()

