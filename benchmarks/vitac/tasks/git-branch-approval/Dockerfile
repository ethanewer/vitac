FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    bash coreutils git python3 python3-pip tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a git repo with main and develop branches
RUN git config --global user.email "test@example.com" && \
    git config --global user.name "Test" && \
    git config --global init.defaultBranch main && \
    git init /app/project && \
    cd /app/project && \
    echo "# My Project" > README.md && \
    git add README.md && \
    git commit -m "Initial commit" && \
    git checkout -b develop && \
    echo "feature code" > feature.py && \
    git add feature.py && \
    git commit -m "Add new feature" && \
    echo "more work" > utils.py && \
    git add utils.py && \
    git commit -m "Add utilities" && \
    git checkout main && \
    # Create a bare remote to push to
    git init --bare /app/remote.git && \
    cd /app/project && \
    git remote add origin /app/remote.git && \
    git push origin main && \
    git checkout develop && \
    git push origin develop
