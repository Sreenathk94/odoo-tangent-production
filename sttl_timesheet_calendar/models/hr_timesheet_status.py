# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrTimesheetStatus(models.Model):
    _name = "hr.timesheet.status"
    _description = "Timesheet Status"
    _order = "sequence asc"

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence')
    project_ids = fields.Many2many("project.project"
                                   ,'allowed_stage_project_rel'
                                   ,string='Projects')

