from odoo import api, fields, models


class PreventModel(models.Model):
    _name = "prevent.model"
    _description = "Prevent Model"

    auto_save_prevent = fields.Boolean("Prevent Auto Save for Specific Model",help="This option allows you to prevent auto-save for a specific model. When enabled, the system will not automatically save changes made to this model.")
    auto_save_prevent_all = fields.Boolean("Prevent Auto Save Globally",help="This option allows you to disable auto-save globally across all models. When enabled, no changes will be automatically saved.")
    model_ids = fields.One2many('prevent.model.line', 'prevent_id', "Select Model", help="Select specific models for which auto-save will be prevented. You can choose multiple models here.")

    @api.onchange('auto_save_prevent')
    def onchange_method_auto_save_prevent(self):
        if self.auto_save_prevent:
            self.auto_save_prevent_all = False
            

    @api.onchange('auto_save_prevent_all')
    def onchange_method_auto_save_prevent_all(self):
        if self.auto_save_prevent_all:
            self.auto_save_prevent = False


