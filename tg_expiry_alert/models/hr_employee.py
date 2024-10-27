from odoo import fields, models, api
from datetime import timedelta


class HrEmployee(models.Model):
    """
    HrEmployee Model

    This model extends the 'hr.employee' model to add a method for
    sending expiry alerts for employee visas, work permits, and passports.
    """

    _inherit = 'hr.employee'

    passport_expire_date = fields.Date(string='Passport Expire Date')

    def action_expiry_alert(self):
        """
        Send expiry alerts for visas, work permits, and passports.

        This method retrieves the configured reminder period for
        document expirations and checks each employee's visa, work
        permit, and passport expiration dates. If an expiration date is
        approaching within the specified reminder period, an email
        alert is sent to the employee, and a consolidated alert is sent
        to all admins.
        """

        expiry_date_reminder = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'tg_expiry_alert.expiry_date_reminder'))
        today = fields.Date.today()
        records = self.env['hr.employee'].search([])
        email_to = self.env.ref("tg_expiry_alert.expiry_alert_admins").users

        # Collect lists for admin email
        visa_expiry_employees = []
        work_permit_expiry_employees = []
        passport_expiry_employees = []

        for rec in records:
            # Visa expiry notification

            if rec.visa_expire:
                visa_reminder_date = rec.visa_expire - timedelta(
                    days=expiry_date_reminder)
                if visa_reminder_date == today:
                    visa_expiry_employees.append(rec.name)
                    visa_template = self.env.ref(
                        "tg_expiry_alert.work_permit_expiry_template")
                    visa_template.send_mail(res_id=rec.id, force_send=True)

            # Work permit expiry notification
            if rec.work_permit_expiration_date:
                work_permit_reminder_date = rec.work_permit_expiration_date - timedelta(
                    days=expiry_date_reminder)
                if work_permit_reminder_date == today:
                    work_permit_expiry_employees.append(rec.name)
                    work_permit_template = self.env.ref(
                        "tg_expiry_alert.work_permit_template")
                    work_permit_template.send_mail(res_id=rec.id,
                                                   force_send=True)

            # Passport expiry notification
            if rec.passport_expire_date:
                passport_reminder_date = rec.passport_expire_date - timedelta(
                    days=expiry_date_reminder)
                if passport_reminder_date == today:
                    passport_expiry_employees.append(rec.name)
                    passport_template = self.env.ref(
                        "tg_expiry_alert.passport_expiry_template")
                    passport_template.send_mail(res_id=rec.id, force_send=True)

        # Send admin email with all expiring documents
        if visa_expiry_employees or work_permit_expiry_employees or passport_expiry_employees:
            admin_template = self.env.ref(
                "tg_expiry_alert.visa_expiry_template_admin")
            for admin in email_to:
                admin_template.with_context(
                    visa_expiry_list=visa_expiry_employees,
                    work_permit_expiry_list=work_permit_expiry_employees,
                    passport_expiry_list=passport_expiry_employees,
                    expiry_date_reminder=expiry_date_reminder,
                ).send_mail(res_id=admin.id, force_send=True)
