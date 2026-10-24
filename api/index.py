import os
import sys

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, init_database

class VercelMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Vercel passes original client URI in HTTP_X_FORWARDED_URI or HTTP_X_MATCHED_PATH
        orig_uri = environ.get('HTTP_X_FORWARDED_URI') or environ.get('HTTP_X_MATCHED_PATH')
        if orig_uri:
            path = orig_uri.split('?')[0]
            if path:
                environ['PATH_INFO'] = path
        elif environ.get('PATH_INFO') in ('/api/index', '/api/index.py', '/api'):
            environ['PATH_INFO'] = '/'
            
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelMiddleware(app.wsgi_app)

# Ensure database tables and doctors are initialized on serverless start
init_database()
