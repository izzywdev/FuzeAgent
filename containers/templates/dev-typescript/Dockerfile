FROM fuzeagent/dev-base:latest

# Install Node.js 18 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - \
    && sudo apt-get install -y nodejs \
    && sudo rm -rf /var/lib/apt/lists/*

# Install Yarn package manager
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list \
    && sudo apt-get update \
    && sudo apt-get install -y yarn \
    && sudo rm -rf /var/lib/apt/lists/*

# Install pnpm
RUN sudo npm install -g pnpm

# Install global TypeScript development tools
RUN sudo npm install -g \
    typescript@latest \
    tsx@latest \
    ts-node@latest \
    nodemon@latest \
    # Build tools
    vite@latest \
    webpack@latest \
    rollup@latest \
    # Testing tools
    jest@latest \
    vitest@latest \
    # Code quality tools
    eslint@latest \
    prettier@latest \
    # Framework CLIs
    @nestjs/cli@latest \
    next@latest \
    # API development
    @apidevtools/swagger-cli@latest \
    # Database tools
    prisma@latest \
    # Development utilities
    concurrently@latest \
    cross-env@latest \
    dotenv-cli@latest

# Set up Node.js development environment
ENV NODE_ENV=development
ENV NPM_CONFIG_PREFIX=/home/agent/.npm-global
ENV PATH=$PATH:/home/agent/.npm-global/bin

# Create npm global directory and set permissions
RUN mkdir -p /home/agent/.npm-global \
    && sudo chown -R agent:agent /home/agent/.npm-global

# Install TypeScript configuration files
COPY tsconfig.json /home/agent/tsconfig.json
COPY package.json /home/agent/package.json
COPY .eslintrc.json /home/agent/.eslintrc.json
COPY .prettierrc /home/agent/.prettierrc

# TypeScript-specific aliases
COPY .typescript_aliases /home/agent/.typescript_aliases
RUN echo "source /home/agent/.typescript_aliases" >> /home/agent/.bashrc

# Set ownership
RUN sudo chown -R agent:agent /home/agent

USER agent
WORKDIR /workspaces

# Welcome message override
RUN echo 'echo "📘 FuzeAgent TypeScript Development Container"' >> /home/agent/.bashrc \
    && echo 'echo "   Node.js: $(node --version)"' >> /home/agent/.bashrc \
    && echo 'echo "   npm: $(npm --version)"' >> /home/agent/.bashrc \
    && echo 'echo "   TypeScript: $(tsc --version)"' >> /home/agent/.bashrc \
    && echo 'echo "   Package Managers: npm, yarn, pnpm"' >> /home/agent/.bashrc