"""
Production WSGI server using Waitress
"""

import os
import sys
from waitress import serve

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == "__main__":
    # Get port from Railway
    port = int(os.environ.get("PORT", 5000))
    
    print("=" * 60)
    print("🚀 PDA SIMULATOR - Production Server (Waitress)")
    print("=" * 60)
    print(f"🌐 Host: 0.0.0.0:{port}")
    print(f"🐍 Python: {sys.version}")
    print("=" * 60)
    
    # Configure for production
    app.config.update(
        ENV='production',
        DEBUG=False,
        TESTING=False
    )
    
    # Create upload folder
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    print(f"📁 Upload folder: {upload_folder}")
    
    # Start Waitress production server
    print("⚙️  Starting Waitress production server...")
    serve(app, host='0.0.0.0', port=port, threads=4)