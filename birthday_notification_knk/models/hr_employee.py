# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>)

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def send_birthday_notification(self):
        today = fields.Date.context_today(self)
        today_month_day = (today.month, today.day)
        employees = self.env['hr.employee'].search([('birthday', '!=', False), ('work_email', '!=', False)])
        all_work_emails = employees.mapped('work_email')
        for employee in employees:
            if employee.birthday:
                employee_month_day = (employee.birthday.month, employee.birthday.day)
                if employee.company_id.send_employee_birthday_notification and today_month_day == employee_month_day:
                    # _logger.info('Birthday email sent to: %sent', employee.work_email)
                    template_id = self.env.ref('birthday_notification_knk.employee_birthday_notification_template')
                    email_values = {
                        'email_cc': ",".join(all_work_emails)
                    }
                    template_id.send_mail(employee.id, force_send=True, email_values=email_values)
