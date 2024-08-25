# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ProjectProject(models.Model):
	_inherit = 'project.project'

	allowed_stage_ids = fields.Many2many(
		"hr.timesheet.status",'allowed_stage_project_rel',string='Stages',order='sequence asc')
	timesheet_status_id = fields.Many2one(
		"hr.timesheet.status",'Stages', order='sequence asc', domain="[('id', 'in', allowed_stage_ids)]")
	timesheet_count = fields.Integer("Timesheet Count",compute="_get_timesheet_count")
	timesheet_duration = fields.Float("Timesheet Durations(HH:MM)",compute="_get_timesheet_duration")
	is_project_start_mail_sent = fields.Boolean("Project Start Mail Sent?",default=False,copy=False)
	stage_cost_ids = fields.One2many('project.cost.stage','project_id',string='Stage wise cost')


	@api.depends('timesheet_ids')
	def _get_timesheet_count(self):
		for rec in self:
			if rec.timesheet_ids:
				rec.timesheet_count = len(rec.timesheet_ids)
			else:
				rec.timesheet_count = 0
				
	@api.depends('timesheet_ids')
	def _get_timesheet_duration(self):
		for rec in self:
			if rec.timesheet_ids:
				rec.timesheet_duration = sum([x.unit_amount for x in rec.timesheet_ids])
			else:
				rec.timesheet_duration = 0
				

class ProjectCostStage(models.Model):
	_name = "project.cost.stage"
	_description = "Project Cost Stage"
	
	project_id = fields.Many2one('project.project', "Project")
	allowed_stage_ids = fields.Many2many(related='project_id.allowed_stage_ids',string='Stages')
	timesheet_status_id = fields.Many2one(
		"hr.timesheet.status",'Stages',domain="[('id', 'in', allowed_stage_ids)]",required=True)
	amount = fields.Float('Amount')
	
	