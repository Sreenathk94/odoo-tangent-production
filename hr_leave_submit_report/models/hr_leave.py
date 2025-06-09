from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, AccessDenied


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def create(self, vals_list):
        """Super the create function in hr.leave to calculate duration days."""
        employee_id = vals_list.get('employee_id')
        leave_type_id = vals_list.get('holiday_status_id')

        if employee_id and leave_type_id:
            employee = self.env['hr.employee'].browse(employee_id)
            leave_type = self.env['hr.leave.type'].browse(leave_type_id)
            if leave_type.code == 'AL' and employee.date_of_join:
                doj = employee.date_of_join
                if isinstance(doj, str):  # if it's a string, convert
                    doj = datetime.strptime(doj, '%Y-%m-%d').date()
                today = datetime.today().date()
                six_months_after_doj = doj + relativedelta(months=6)
                if today < six_months_after_doj:
                    raise ValidationError("Employee is under probation and cannot take annual leave.")
        res = super(HrLeave, self).create(vals_list)
        if res.holiday_status_id.id == res.env.ref(
                'hr_holidays.holiday_status_sl').id:
            if res.number_of_days_display and res.number_of_days_display >= 2 and not res.supported_attachment_ids:
                raise ValidationError(
                    "Employee must submit the attachment or medical report for sick leave of 2 or more consecutive days.")
            if res.number_of_days_display and res.number_of_days_display == 1 and not res.supported_attachment_ids:
                request_date_from = res.request_date_from
                date_obj = fields.Date.from_string(res.request_date_from)
                # Check if the day is Monday (0) or Friday (4)
                if date_obj.weekday() in (0, 4):
                    day = "Monday" if date_obj.weekday() == 0 else "Friday"
                    raise ValidationError(
                        f"Employee must submit an attachment or medical report if the leave starts on {day}"
                    )
        return res

    @api.constrains('supported_attachment_ids')
    def _onchange_supported_attachment_ids(self):
        """This onchange method is used set validation if attatchment desont
        exist"""
        if not self.supported_attachment_ids:
            if self.holiday_status_id.id == self.env.ref(
                    'hr_holidays.holiday_status_sl').id:
                if self.number_of_days_display and self.number_of_days_display >= 2 and not self.supported_attachment_ids:
                    raise ValidationError(
                        "Employee must submit the attachment or medical report for sick leave of 2 or more consecutive days.")
                if self.number_of_days_display and self.number_of_days_display == 1 and not self.supported_attachment_ids:
                    date_obj = fields.Date.from_string(self.request_date_from)
                    # Check if the day is Monday (0) or Friday (4)
                    if date_obj.weekday() in (0, 4):
                        day = "Monday" if date_obj.weekday() == 0 else "Friday"
                        raise ValidationError(
                            f"Employee must submit an attachment or medical report if the leave starts on {day}"
                        )

    def action_refuse(self):
        """
        Overrides the default action_refuse method to display a wizard for collecting
        a refusal reason before proceeding with the leave refusal.

        The wizard popup is displayed unless the `skip_wizard` context key is present.
        If the wizard is completed, it saves the reason and then calls the original
        action_refuse to apply the refusal logic.

        Returns:
            dict: Action dictionary to open the wizard window, or the result of the
                  original action_refuse when skip_wizard is in context.
        """
        if self.env.context.get('skip_wizard'):
            # Call the default action_refuse when skip_wizard is set in context
            return super(HrLeave, self).action_refuse()
        else:
            # Otherwise, open the wizard to capture the refusal reason
            return {
                'type': 'ir.actions.act_window',
                'name': 'Refuse Leave',
                'res_model': 'hr.leave.refuse.wizard',
                'view_mode': 'form',
                'views': [[False, "form"]],
                'target': 'new',
                'context': {'active_id': self.id},
            }

    @api.depends('number_of_hours_display', 'number_of_days_display', 'request_unit_half', 'leave_type_request_unit')
    def _compute_duration_display(self):
        """
        Compute the human-readable duration string for a leave request.

        If the leave is based on hours or days, display the rounded value with appropriate units.
        If the leave is a half-day request (request_unit_half is True and leave_type_request_unit is 'half_day'),
        override the display to show '0.5 days' regardless of the actual computed number of days.
        """
        super()._compute_duration_display()
        for leave in self:
            if leave.leave_type_request_unit == 'half_day' and leave.request_unit_half:
                leave.duration_display = '0.5 %s' % _('days')

    def _get_leaves_on_public_holiday(self):
        """
        Return leaves on public holidays where the number of hours is zero.

        This method overrides the parent implementation to further filter
        the leaves returned by the superclass method, excluding those with
        any hours logged (i.e., keeps only leaves with 0 hours).

        Returns:
            recordset: Filtered leave records with zero `number_of_hours`.
        """
        return super()._get_leaves_on_public_holiday().filtered(lambda l: not l.number_of_hours)
