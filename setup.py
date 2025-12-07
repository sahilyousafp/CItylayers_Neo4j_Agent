"""
Setup script for Location Agent
Handles installation, environment setup, and initial configuration
"""
import os
import sys
import subprocess
from pathlib import Path

def print_header(message):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60 + "\n")

def check_python_version():
    """Verify Python version is 3.8+"""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    print("✅ Python version OK")

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    print_header("Checking Environment Configuration")
    
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("⚠️  .env file not found. Creating from template...")
    
    env_template = """# Neo4j Configuration
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Google Gemini Configuration
# Get your API key from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY_HERE
GOOGLE_MODEL=gemini-2.0-flash-exp

# Flask Configuration
FLASK_SECRET_KEY=dev-secret-key-change-in-production

# Mapbox
MAPBOX_ACCESS_TOKEN=your-mapbox-token
"""
    
    with open(".env", "w") as f:
        f.write(env_template)
    
    print("✅ Created .env file - Please update with your credentials!")

def install_dependencies():
    """Install required Python packages"""
    print_header("Installing Dependencies")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)

def verify_installation():
    """Verify that key packages can be imported"""
    print_header("Verifying Installation")
    
    required_packages = [
        "flask",
        "langchain",
        "langchain_google_genai",
        "langchain_neo4j",
        "neo4j",
        "pandas"
    ]
    
    failed = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            failed.append(package)
    
    if failed:
        print(f"\n⚠️  Failed to import: {', '.join(failed)}")
        print("Try running: pip install -r requirements.txt")
    else:
        print("\n✅ All packages verified!")

def print_next_steps():
    """Display next steps for the user"""
    print_header("Setup Complete!")
    
    print("""
Next Steps:

1. Configure your .env file with actual credentials:
   - NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
   - GOOGLE_API_KEY (get from https://makersuite.google.com/app/apikey)
   - MAPBOX_ACCESS_TOKEN

2. Run the application:
   python app.py

3. Access the app at:
   http://localhost:5000

For more information, see README.md
""")

def main():
    """Main setup routine"""
    print_header("Location Agent Setup")
    
    check_python_version()
    create_env_file()
    install_dependencies()
    verify_installation()
    print_next_steps()

if __name__ == "__main__":
    main()
