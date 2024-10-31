from odoo import models, fields, api


class HrLeaveRefuseWizard(models.TransientModel):
    """
    A transient model representing the wizard for entering a reason to refuse a leave.
    It captures the refusal reason and triggers the default `action_refuse` behavior on
    the associated leave record.
    """
    _name = 'hr.leave.refuse.wizard'
    _description = 'Refuse Reason Wizard for Leave'

    refuse_reason = fields.Text(string="Refuse Reason", required=True,
                                help="The reason for refusing the leave request.")

    def action_confirm_refuse(self):
        """
         This method is called when the user confirms the refusal in the wizard.
        It saves the refusal reason to the corresponding leave record, posts a message
        in the chatter, and triggers the default action_refuse functionality to finalize
        the refusal.

        It uses the `skip_wizard` context key to avoid reopening the wizard when
        `action_refuse` is called.
        """
        leave = self.env['hr.leave'].browse(self.env.context.get('active_id'))
        leave.with_context(skip_wizard=True).action_refuse()
        leave.message_post(
            body=f"Leave request refused. Reason: {self.refuse_reason}",
            subject="Leave Refused"
        )
