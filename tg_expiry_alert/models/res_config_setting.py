"""
Module: res_config_settings
----------------------------
Usage:
------
This module can be used to configure how many days in advance
the system should remind users about document expiry dates.
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """
    ResConfigSettings Model

    This model extends the 'res.config.settings' model to introduce
    a new integer field that allows users to set a reminder for
    expiry dates of documents.

    """

    _inherit = 'res.config.settings'

    expiry_date_reminder = fields.Integer(
        string='Expiry date reminder',
        config_parameter='tg_expiry_alert.expiry_date_reminder',
        help='Expiry date reminder for documents'
    )
