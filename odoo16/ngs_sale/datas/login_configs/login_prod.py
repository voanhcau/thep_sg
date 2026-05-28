import os
try:
import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib

username = os.getenv("ODOO_USERNAME")
password = os.getenv("ODOO_PASSWORD")

if not username or not password:
    raise ValueError("ODOO_USERNAME and ODOO_PASSWORD environment variables must be set")

db = os.getenv("ODOO_DB")
url = os.getenv("ODOO_URL")

if not db or not url:
    raise ValueError("ODOO_DB and ODOO_URL environment variables must be set")

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
