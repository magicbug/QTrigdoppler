#!/bin/bash

echo "Installing Node.js dependencies for QTrigdoppler Remote Server"
echo "============================================================"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in your PATH."
    echo "Please install Node.js from https://nodejs.org/"
    echo "or use your system's package manager (apt, yum, etc.)"
    echo "Then run this script again."
    exit 1
fi

# Display Node.js version
echo "Using Node.js:"
node --version

# Install dependencies
echo
echo "Installing required packages..."
npm install express socket.io ini

echo
echo "============================================================"
echo "Installation complete!"
echo
echo "To start the remote server:"
echo "    node remote_server.js"
echo
echo "After starting, you can configure QTrigdoppler to connect to it by"
echo "editing config.ini:"
echo
echo "[remote_server]"
echo "enable = True"
echo "url = http://localhost:5001"
echo "port = 5001"
echo "debug = False"
echo
echo "============================================================"
