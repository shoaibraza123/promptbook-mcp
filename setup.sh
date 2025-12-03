#!/bin/bash
# setup.sh - One-command setup for MCP Prompt Library

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

# Banner
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   🤖 MCP Prompt Library Setup                ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

# Check Python version
print_step "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
    print_error "Python 3.9+ required. Found: $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Create virtual environment
print_step "Creating virtual environment..."
if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists. Skipping creation."
else
    python3 -m venv .venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_step "Activating virtual environment..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    print_success "Virtual environment activated"
else
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
print_step "Upgrading pip..."
python -m pip install --upgrade pip --quiet
print_success "pip upgraded"

# Install dependencies
print_step "Installing dependencies..."
pip install -r requirements.txt --quiet

# Check if installation succeeded
if [ $? -eq 0 ]; then
    print_success "Dependencies installed"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Create necessary directories
print_step "Creating directories..."
mkdir -p prompts sessions
mkdir -p prompts/{refactoring,testing,debugging,implementation,documentation,general,code-review}
print_success "Directories created"

# Create .env file if not exists
if [ ! -f ".env" ]; then
    print_step "Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please review and update .env file with your settings"
    else
        print_warning ".env.example not found. Skipping .env creation."
    fi
else
    print_warning ".env already exists. Not overwriting."
fi

# Index prompts (if any exist)
print_step "Indexing prompts..."
PROMPT_COUNT=$(find prompts -name "*.md" -not -name "README.md" 2>/dev/null | wc -l | tr -d ' ')

if [ "$PROMPT_COUNT" -gt 0 ]; then
    print_step "Found $PROMPT_COUNT prompts. Indexing..."
    python prompt_rag.py --index
    print_success "Prompts indexed"
else
    print_warning "No prompts found. You can add prompts later and run: python prompt_rag.py --index"
fi

# Final instructions
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   ✅ Setup Complete!                          ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "📚 Next steps:"
echo ""
echo "  1. Review configuration:"
echo "     ${BLUE}nano .env${NC}"
echo ""
echo "  2. Start the MCP server:"
echo "     ${GREEN}python mcp_server.py${NC}"
echo ""
echo "  3. Or use Docker:"
echo "     ${GREEN}docker-compose up -d${NC}"
echo ""
echo "📖 Documentation: ./README.md"
echo ""
echo "Happy prompting! 🚀"
echo ""
