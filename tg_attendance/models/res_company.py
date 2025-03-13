from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'


    ramadan_start_date = fields.Date('Ramadan Start Date')
    ramadan_end_date = fields.Date('Ramadan End Date')
    ramadan_total_work_time = fields.Float('Ramadan Working Time')
