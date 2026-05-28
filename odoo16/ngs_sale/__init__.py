from . import controllers
from . import models
from . import reports
from . import wizards

from odoo import api, fields, models, _

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def _auto_clean_cache_when_installed(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].sudo().set_param('pos_template installed times', fields.Date.today())
