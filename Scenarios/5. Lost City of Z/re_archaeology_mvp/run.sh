#!/bin/bash

# RE-Archaeology Agent MVP Startup Script

echo "Starting RE-Archaeology Agent MVP..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Please install Docker and Docker Compose."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating default .env file..."
    cat > .env << EOL
DATABASE_URL=postgresql://re_archaeology:re_archaeology_pass@db:5432/re_archaeology_db
REDIS_URL=redis://redis:6379/0
# Uncomment and set these for Earth Engine integration
# EARTH_ENGINE_PRIVATE_KEY=your-private-key
# EARTH_ENGINE_SERVICE_ACCOUNT=your-service-account
EOL
fi

# Start the Docker containers
echo "Starting Docker containers..."
docker-compose up -d

# Wait for the services to start
echo "Waiting for services to start..."
sleep 5

# Check if PostgreSQL is running
echo "Checking database connection..."
if ! docker-compose exec db pg_isready -U re_archaeology > /dev/null 2>&1; then
    echo "Database is not ready yet. Waiting additional time..."
    sleep 10
    if ! docker-compose exec db pg_isready -U re_archaeology > /dev/null 2>&1; then
        echo "Error: Database failed to start properly."
        echo "Check logs with: docker-compose logs db"
        exit 1
    fi
fi

# Check if backend API is running
echo "Checking backend API..."
API_READY=false
for i in {1..10}; do
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        API_READY=true
        break
    fi
    echo "Waiting for API to be ready... ($i/10)"
    sleep 3
done

if [ "$API_READY" = false ]; then
    echo "Error: API failed to start properly."
    echo "Check logs with: docker-compose logs backend"
    exit 1
fi

# Open browser
echo "Opening web interface..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000/frontend/index.html
elif command -v open &> /dev/null; then
    open http://localhost:8000/frontend/index.html
else
    echo "Web interface available at: http://localhost:8000/frontend/index.html"
fi

echo ""
echo "RE-Archaeology Agent MVP is running!"
echo "Web interface: http://localhost:8000/frontend/index.html"
echo "API documentation: http://localhost:8000/docs"
echo ""
echo "To stop the application, run: docker-compose down"
