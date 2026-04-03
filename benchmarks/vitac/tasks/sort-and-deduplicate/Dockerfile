FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/data /app/output && cat > /app/data/records.csv << 'EOF'
id,name,score
3,Charlie,85
1,Alice,92
2,Bob,78
1,Alice,92
4,Diana,95
2,Bob,78
5,Eve,88
3,Charlie,85
EOF
