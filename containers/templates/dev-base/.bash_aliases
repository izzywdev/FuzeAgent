# FuzeAgent Development Aliases

# Git shortcuts
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline'
alias gd='git diff'

# Docker shortcuts
alias dps='docker ps'
alias di='docker images'
alias dlog='docker logs'
alias dexec='docker exec -it'

# Development shortcuts
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'

# FuzeAgent specific
alias agent-status='python3 /usr/local/bin/autonomous_agent_with_memory.py --status'
alias agent-logs='tail -f /tmp/agent.log'
alias workspace='cd /workspaces'

# Python shortcuts
alias py='python3'
alias pip='python3 -m pip'
alias venv='python3 -m venv'

# Utility functions
function mkcd() {
    mkdir -p "$1" && cd "$1"
}

function backup() {
    cp "$1" "$1.backup.$(date +%Y%m%d_%H%M%S)"
}
EOF < /dev/null
