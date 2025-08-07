#!/bin/bash

echo "=========================================="
echo "HUMANSA AI AGENT B2 - SETUP SCRIPT"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ "$1" = "success" ]; then
        echo -e "${GREEN}✅ $2${NC}"
    elif [ "$1" = "error" ]; then
        echo -e "${RED}❌ $2${NC}"
    else
        echo -e "${YELLOW}⚠️  $2${NC}"
    fi
}

# Check if we're in the correct directory
if [ ! -f "requirements.txt" ]; then
    print_status "error" "requirements.txt not found. Please run this script from the ML server directory."
    exit 1
fi

echo "Step 1: Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR_VERSION" -lt 3 ] || [ "$MINOR_VERSION" -lt 8 ]; then
    print_status "error" "Python 3.8+ is required. Current version: $PYTHON_VERSION"
    exit 1
else
    print_status "success" "Python version $PYTHON_VERSION is compatible"
fi

echo ""
echo "Step 2: Setting up virtual environment..."

# Remove old virtual environment if it exists
if [ -d "youwo-ml-venv" ]; then
    print_status "warning" "Existing virtual environment found. Removing..."
    rm -rf youwo-ml-venv
fi

# Create new virtual environment
print_status "info" "Creating new virtual environment..."
python3 -m venv youwo-ml-venv

if [ $? -eq 0 ]; then
    print_status "success" "Virtual environment created successfully"
else
    print_status "error" "Failed to create virtual environment"
    exit 1
fi

echo ""
echo "Step 3: Activating virtual environment..."
source youwo-ml-venv/bin/activate

if [ $? -eq 0 ]; then
    print_status "success" "Virtual environment activated"
else
    print_status "error" "Failed to activate virtual environment"
    exit 1
fi

echo ""
echo "Step 4: Upgrading pip..."
python3 -m pip install --upgrade pip

echo ""
echo "Step 5: Installing dependencies..."
echo "This may take a few minutes..."

# Install dependencies with specific handling for problematic packages
pip install --no-cache-dir -r requirements.txt

if [ $? -eq 0 ]; then
    print_status "success" "All dependencies installed successfully"
else
    print_status "warning" "Some dependencies failed to install. Trying alternative approach..."
    
    # Try installing core dependencies first
    pip install Quart==0.20.0 quart-cors==0.7.0
    pip install aiofiles==24.1.0 aiohttp==3.11.18
    pip install httpx==0.28.1 requests==2.32.3
    
    # Install LlamaIndex packages
    pip install llama-index==0.12.43
    
    # Install database packages
    pip install psycopg2-binary==2.9.10 pgvector SQLAlchemy asyncpg==0.30.0
    
    # Install data processing packages with compatible versions
    pip install pandas numpy scikit-learn beautifulsoup4 pypdf pillow
    
    # Install remaining packages
    pip install python-pptx youtube-transcript-api python-dotenv pydantic tiktoken tenacity PyYAML click uvicorn fastapi
fi

echo ""
echo "Step 6: Creating .env template..."

if [ ! -f ".env" ]; then
    cat > .env.template << 'EOF'
# Required Environment Variables for Humansa AI Agent B2

# OpenAI API Key (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (Required)
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=your_db_username
DB_ACTIVE_DATABASE=your_database_name
DB_PASSWORD=your_db_password

# Optional LLM Providers
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
XAI_API_KEY=your_xai_api_key
GOOGLE_API_KEY=your_google_api_key

# Optional Web Search APIs (choose one)
SERPER_API_KEY=your_serper_api_key
SERPAPI_API_KEY=your_serpapi_api_key
BING_SEARCH_API_KEY=your_bing_api_key

# Server Configuration
ML_SERVER_PORT=5001
EOF
    print_status "success" "Created .env.template file"
    print_status "warning" "Please copy .env.template to .env and fill in your API keys"
else
    print_status "info" ".env file already exists"
fi

echo ""
echo "Step 7: Running diagnostic test..."
python3 test_humansa_agent_b2.py

echo ""
echo "=========================================="
echo "SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy .env.template to .env and add your API keys"
echo "2. Ensure PostgreSQL database is running"
echo "3. Run the server with: source youwo-ml-venv/bin/activate && python src/main.py"
echo "4. Test the setup with: python test_humansa_agent_b2.py"
echo ""
print_status "info" "To activate the virtual environment in the future, run:"
echo "    source youwo-ml-venv/bin/activate"