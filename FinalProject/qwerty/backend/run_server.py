import sys
import os
# When run directly (python backend/run_server.py) the package root may not be on sys.path.
# Ensure project root is first on sys.path so `import backend.server` works.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.server import app, init_db
import signal

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Server stopped by user")
    sys.exit(0)

def main():
    """Main entry point for the application"""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize database
    with app.app_context():
        init_db()
        print("✅ Database initialized")
    
    # Read server configuration from environment variables
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '1') in ('1', 'true', 'True')
    use_reloader = os.environ.get('FLASK_RELOAD', '1') in ('1', 'true', 'True')

    # Start the server
    print(f"🚀 Starting Hub E-Commerce Platform on http://{host}:{port}")
    try:
        app.run(
            debug=debug,
            host=host,
            port=port,
            use_reloader=use_reloader
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except SystemExit:
        pass

if __name__ == '__main__':
    main()
