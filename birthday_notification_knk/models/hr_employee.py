# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>)

from odoo import api, fields, models
import logging


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def send_birthday_notification(self):
        _logger = logging.getLogger(__name__)  # Corrected logger
        today = fields.Date.context_today(self)
        today_month_day = (today.month, today.day)
        employees = self.env['hr.employee'].search([('birthday', '!=', False), ('work_email', '!=', False)])
        for employee in employees:
            if employee.birthday:
                employee_month_day = (employee.birthday.month, employee.birthday.day)
                _logger.info('Checking birthday for: %s', employee.name)  # Corrected logging
                if employee.company_id.send_employee_birthday_notification and today_month_day == employee_month_day:
                    _logger.info('Sending birthday notification to: %s', employee.name)
                    template_id = self.env.ref('birthday_notification_knk.employee_birthday_notification_template')
                    if template_id:
                        template_id.send_mail(employee.id, force_send=True)
                    else:
                        _logger.warning('Email template not found!')
