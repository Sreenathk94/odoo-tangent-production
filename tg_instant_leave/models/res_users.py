from odoo import models

class ResUsers(models.Model):
    _inherit = 'res.users'

    def grant_urgent_leave_creator(self):
        group = self.env.ref('tg_instant_leave.group_urgent_leave_creator')
        self.groups_id |= group

    def grant_urgent_leave_admin(self):
        group = self.env.ref('tg_instant_leave.group_urgent_leave_admin')
        self.groups_id |= group