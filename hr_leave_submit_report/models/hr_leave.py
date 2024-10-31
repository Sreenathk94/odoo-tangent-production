from odoo import api, models, fields
from datetime import datetime, time

from odoo.exceptions import ValidationError, AccessDenied


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def create(self, vals_list):
        """Super the create function in hr.leave to calculate duration days."""

        res = super(HrLeave, self).create(vals_list)
        if res.holiday_status_id.id == res.env.ref(
                'hr_holidays.holiday_status_sl').id:
            if res.number_of_days_display and res.number_of_days_display >= 2 and not res.supported_attachment_ids:
                raise ValidationError(
                    "Employee must submit the attachment or medical report for sick leave of 2 or more consecutive days.")
            if res.number_of_days_display and res.number_of_days_display == 1 and not res.supported_attachment_ids:
                request_date_from = res.request_date_from
                print("request_date_from", request_date_from)
                date_obj = fields.Date.from_string(res.request_date_from)
                # Check if the day is Monday (0) or Friday (4)
                print("Check", date_obj)
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
            print("ttttttttttttttttttt")
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
