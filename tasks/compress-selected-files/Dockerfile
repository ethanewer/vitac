FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/data /app/output && \
    echo "id,name,value" > /app/data/users.csv && \
    echo "1,Alice,100" >> /app/data/users.csv && \
    echo "id,product,price" > /app/data/products.csv && \
    echo "1,Widget,9.99" >> /app/data/products.csv && \
    echo "id,order,total" > /app/data/orders.csv && \
    echo "1,ORD001,29.97" >> /app/data/orders.csv && \
    echo "temporary data" > /app/data/cache.tmp && \
    echo "debug output" > /app/data/debug.log && \
    echo "more temp" > /app/data/session.tmp
