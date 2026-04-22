# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    import os
    from waitress import serve
    
    port = int(os.environ.get('FLASK_PORT', 5000))
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    
    # Use waitress for production (works on Windows and Linux)
    serve(app, host=host, port=port, threads=4)