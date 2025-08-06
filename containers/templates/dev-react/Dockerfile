FROM fuzeagent/dev-typescript:latest

# Install React-specific global tools
RUN sudo npm install -g \
    create-react-app@latest \
    @vitejs/create-app@latest \
    @storybook/cli@latest \
    react-devtools@latest \
    @testing-library/react@latest

# Install additional development tools for React
RUN sudo npm install -g \
    # Styling and UI
    tailwindcss@latest \
    @headlessui/react@latest \
    @heroicons/react@latest \
    # State management
    @reduxjs/toolkit@latest \
    zustand@latest \
    # Routing
    react-router-dom@latest \
    # Testing
    @testing-library/jest-dom@latest \
    @testing-library/user-event@latest \
    # Build and dev tools
    @craco/craco@latest \
    react-scripts@latest

# Install React development configurations
COPY package.json /home/agent/react-package.json
COPY vite.config.ts /home/agent/vite.config.ts
COPY tailwind.config.js /home/agent/tailwind.config.js
COPY postcss.config.js /home/agent/postcss.config.js
COPY .storybook/ /home/agent/.storybook/

# React-specific aliases
COPY .react_aliases /home/agent/.react_aliases
RUN echo "source /home/agent/.react_aliases" >> /home/agent/.bashrc

# Set React environment variables
ENV REACT_APP_NODE_ENV=development
ENV BROWSER=none
ENV GENERATE_SOURCEMAP=true
ENV SKIP_PREFLIGHT_CHECK=true

# Set ownership
RUN sudo chown -R agent:agent /home/agent

USER agent
WORKDIR /workspaces

# Welcome message override
RUN echo 'echo "⚛️  FuzeAgent React Development Container"' >> /home/agent/.bashrc \
    && echo 'echo "   React: Ready for development"' >> /home/agent/.bashrc \
    && echo 'echo "   Tools: Vite, Tailwind, Storybook, Testing Library"' >> /home/agent/.bashrc \
    && echo 'echo "   UI: React Router, Headless UI, Heroicons"' >> /home/agent/.bashrc