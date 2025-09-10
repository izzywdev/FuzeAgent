# FuzeAgent Mock Server + UI Deployment

This deployment includes only the Mock Server and UI components, configured to access the database at IP `172.17.0.2`.

## Quick Start

### Option 1: Using the provided scripts (Recommended)

**For Windows:**
```bash
run-mock-ui.bat
```

**For Linux/Mac:**
```bash
chmod +x run-mock-ui.sh
./run-mock-ui.sh
```

### Option 2: Manual setup

1. **Start the Mock Server:**
   ```bash
   docker-compose -f docker-compose.mock-ui.yml up -d
   ```

2. **Start the UI (in a separate terminal):**
   ```bash
   cd services/ui-react
   set REACT_APP_API_URL=http://localhost:8001
   npm install --legacy-peer-deps
   npm start
   ```

## Services

### Mock Server
- **URL:** http://localhost:8001
- **Health Check:** http://localhost:8001/health
- **API Docs:** http://localhost:8001/docs
- **Database:** PostgreSQL at 172.17.0.2:5432

### UI (React)
- **URL:** http://localhost:3000
- **Mode:** Development with hot reload
- **API Endpoint:** http://localhost:8001

## Configuration

The Mock Server is configured to connect to the database at `172.17.0.2:5432` with the following credentials:
- Database: `ariWeinberg`
- Username: `ariWeinberg`
- Password: `ariWeinberg`

## Stopping Services

To stop the services:

```bash
# Stop Docker services
docker-compose -f docker-compose.mock-ui.yml down

# Stop UI (if running manually)
# Press Ctrl+C in the terminal where npm start is running
```

## Troubleshooting

1. **Mock Server not responding:**
   - Check if the database at 172.17.0.2 is accessible
   - Verify Docker container is running: `docker ps`
   - Check logs: `docker-compose -f docker-compose.mock-ui.yml logs mock-server`

2. **UI not connecting to API:**
   - Ensure `REACT_APP_API_URL=http://localhost:8001` is set
   - Check if Mock Server is running and accessible

3. **Database connection issues:**
   - Verify the database is running at 172.17.0.2:5432
   - Check network connectivity to the database server
