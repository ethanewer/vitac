FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/data /app/output && cat > /app/data/users.csv << 'EOF'
id,username,role
1,alice,admin
2,bob,user
3,charlie,user
4,alice,admin
5,diana,editor
6,bob,user
7,eve,viewer
EOF
