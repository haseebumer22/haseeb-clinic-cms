import os
import sys

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import request, redirect, url_for
from app import app, init_database

@app.before_request
def inspect_headers():
    # Log incoming headers to identify exact Vercel header
    print("VERCEL_HEADERS:", {k: v for k, v in request.headers.items() if not k.lower().startswith('cookie')})
    print("VERCEL_ENV_PATH:", request.environ.get('PATH_INFO'))

# Route /api/index directly to index view so root requests never 404
@app.route('/api/index', methods=['GET', 'POST'])
def vercel_root():
    # If there is a matched path header for another route, route to it
    matched = (
        request.headers.get('x-matched-path') or 
        request.headers.get('x-forwarded-uri') or 
        request.headers.get('x-real-url')
    )
    if matched and matched not in ('/', '/api/index', '/api/index.py'):
        # Clean path
        clean_path = matched.split('?')[0]
        # Match against app url_map
        adapter = app.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match(clean_path, method=request.method)
            return app.view_functions[endpoint](**values)
        except Exception as e:
            print(f"Routing to {clean_path} failed: {e}")
            
    return app.view_functions['index']()

init_database()
