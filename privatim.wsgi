import os
from pyramid.paster import setup_logging
from pyramid.paster import get_app

dir = os.path.dirname(__file__)
ini_path = os.path.join(dir, 'production.ini')

setup_logging(ini_path)
application = get_app(ini_path, 'main')