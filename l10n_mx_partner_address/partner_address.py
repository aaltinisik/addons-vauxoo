# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#
#    Copyright (c) 2010 Vauxoo - http://www.vauxoo.com/
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
############################################################################
#    Coded by: moylop260 (moylop260@vauxoo.com)
############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from osv import fields
from tools.translate import _

class res_partner_address(osv.osv):
    _inherit = 'res.partner.address'
    
    _columns = {
        'street3': fields.char('Street3', size=128),
        'street4': fields.char('Street4', size=128),
        'city2': fields.char('City2', size=128),
    }
    
    def _get_default_country_id(self, cr, uid, context=None):
        country_obj = self.pool.get('res.country')
        #ids = country_obj.search(cr, uid, [ ( 'name', '=', 'México' ), ], limit=1)
        ids = country_obj.search(cr, uid, [ ( 'code', '=', 'MX' ), ], limit=1)
        id = ids and ids[0] or False
        return id
    
    _defaults = {
        'country_id': _get_default_country_id,
    }
res_partner_address()
