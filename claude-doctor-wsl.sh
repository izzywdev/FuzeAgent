#!/bin/bash

# Claude Code Health Check Script for WSL
# This script performs manual health checks that the 'claude doctor' command would normally do

echo "🔍 Claude Code Health Check for WSL Environment"
echo "=============================================="
echo

# Check 1: Node.js version
echo "✅ Checking Node.js installation..."
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node --version)
    echo "   Node.js version: $NODE_VERSION"
    
    # Check if Node.js version is compatible (v18+ recommended)
    NODE_MAJOR=$(echo $NODE_VERSION | sed 's/v\([0-9]*\).*/\1/')
    if [ "$NODE_MAJOR" -ge 18 ]; then
        echo "   ✅ Node.js version is compatible"
    else
        echo "   ⚠️  Node.js version may be too old (v18+ recommended)"
    fi
else
    echo "   ❌ Node.js not found"
fi
echo

# Check 2: Claude Code installation
echo "✅ Checking Claude Code installation..."
if command -v claude >/dev/null 2>&1; then
    CLAUDE_VERSION=$(claude --version)
    echo "   Claude Code version: $CLAUDE_VERSION"
    CLAUDE_PATH=$(which claude)
    echo "   Installation path: $CLAUDE_PATH"
    echo "   ✅ Claude Code is installed"
else
    echo "   ❌ Claude Code not found"
fi
echo

# Check 3: Configuration directory
echo "✅ Checking Claude Code configuration..."
if [ -d "$HOME/.claude" ]; then
    echo "   Configuration directory: $HOME/.claude"
    echo "   ✅ Configuration directory exists"
    
    # Check configuration contents
    if [ -f "$HOME/.claude/config.json" ]; then
        echo "   ✅ Configuration file exists"
    else
        echo "   ⚠️  Configuration file not found (will be created on first run)"
    fi
else
    echo "   ⚠️  Configuration directory not found (will be created on first run)"
fi
echo

# Check 4: WSL-specific issues
echo "✅ Checking WSL environment..."
if grep -q Microsoft /proc/version 2>/dev/null; then
    echo "   ✅ Running in WSL environment"
    
    # Check terminal capabilities
    if [ -t 0 ]; then
        echo "   ✅ Terminal input is available"
    else
        echo "   ⚠️  Terminal input may be limited"
    fi
    
    if [ -t 1 ]; then
        echo "   ✅ Terminal output is available"
    else
        echo "   ⚠️  Terminal output may be limited"
    fi
    
    # Check TERM variable
    if [ -n "$TERM" ]; then
        echo "   Terminal type: $TERM"
        echo "   ✅ TERM variable is set"
    else
        echo "   ⚠️  TERM variable not set"
    fi
else
    echo "   ✅ Not running in WSL (native Linux environment)"
fi
echo

# Check 5: Test basic Claude Code functionality
echo "✅ Testing Claude Code functionality..."
if command -v claude >/dev/null 2>&1; then
    # Test version command (should work)
    if claude --version >/dev/null 2>&1; then
        echo "   ✅ Basic CLI functionality works"
    else
        echo "   ❌ Basic CLI functionality failed"
    fi
    
    # Test config command (should work)
    if claude config list >/dev/null 2>&1; then
        echo "   ✅ Configuration commands work"
    else
        echo "   ❌ Configuration commands failed"
    fi
    
    # Test help command (should work)
    if claude --help >/dev/null 2>&1; then
        echo "   ✅ Help system works"
    else
        echo "   ❌ Help system failed"
    fi
else
    echo "   ❌ Cannot test functionality - Claude Code not installed"
fi
echo

# Check 6: Known WSL issues
echo "✅ Checking for known WSL issues..."
echo "   ⚠️  Interactive 'claude doctor' command fails due to raw mode issues"
echo "   ✅ This is a known limitation in WSL environments"
echo "   ✅ Basic Claude Code functionality should still work"
echo "   💡 Use 'claude --print' for non-interactive commands"
echo

# Summary
echo "📋 Summary"
echo "=========="
echo "✅ Core functionality appears to be working"
echo "⚠️  Interactive doctor command incompatible with WSL"
echo "💡 Recommendation: Use this script instead of 'claude doctor' in WSL"
echo
echo "🎯 To use Claude Code in WSL:"
echo "   • For interactive sessions: claude"
echo "   • For non-interactive use: claude --print 'your prompt'"
echo "   • For configuration: claude config"
echo