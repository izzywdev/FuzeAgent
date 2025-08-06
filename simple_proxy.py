#!/usr/bin/env python3
"""
Simple proxy server that adds organization/team endpoints to the existing API
"""

import asyncio
import asyncpg
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import requests
import uuid
from datetime import datetime

# Configuration
DATABASE_URL = "postgresql://postgres:J7hplO7vKnbUsKDAsxpe4t9C0@localhost:5434/ai_context"
ORIGINAL_API = "http://localhost:8000"
PORT = 8003

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/organizations'):
            asyncio.run(self.handle_organizations_get())
        elif self.path.startswith('/teams'):
            asyncio.run(self.handle_teams_get())
        else:
            self.proxy_request()
    
    def do_POST(self):
        if self.path == '/organizations':
            asyncio.run(self.handle_organizations_post())
        elif self.path == '/teams':
            asyncio.run(self.handle_teams_post())
        else:
            self.proxy_request()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    async def handle_organizations_get(self):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                rows = await conn.fetch("""
                    SELECT 
                        id::text, name, description, settings,
                        created_at::text, updated_at::text
                    FROM organizations 
                    ORDER BY created_at DESC
                """)
                
                organizations = []
                for row in rows:
                    organizations.append({
                        'id': row['id'],
                        'name': row['name'],
                        'description': row['description'],
                        'settings': row['settings'] or {},
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(organizations).encode())
                
            finally:
                await conn.close()
        except Exception as e:
            self.send_error(500, str(e))
    
    async def handle_organizations_post(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                org_id = str(uuid.uuid4())
                row = await conn.fetchrow("""
                    INSERT INTO organizations (id, name, description, settings)
                    VALUES ($1, $2, $3, $4)
                    RETURNING 
                        id::text, name, description, settings,
                        created_at::text, updated_at::text
                """, org_id, data['name'], data.get('description'), json.dumps(data.get('settings', {})))
                
                result = {
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'settings': row['settings'] or {},
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            finally:
                await conn.close()
        except Exception as e:
            self.send_error(500, str(e))
    
    async def handle_teams_get(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)
            organization_id = query_params.get('organization_id', [None])[0]
            
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                if organization_id:
                    rows = await conn.fetch("""
                        SELECT 
                            id::text, organization_id::text, name, description,
                            team_type, settings, created_at::text, updated_at::text
                        FROM teams 
                        WHERE organization_id = $1
                        ORDER BY created_at DESC
                    """, organization_id)
                else:
                    rows = await conn.fetch("""
                        SELECT 
                            id::text, organization_id::text, name, description,
                            team_type, settings, created_at::text, updated_at::text
                        FROM teams 
                        ORDER BY created_at DESC
                    """)
                
                teams = []
                for row in rows:
                    teams.append({
                        'id': row['id'],
                        'organization_id': row['organization_id'],
                        'name': row['name'],
                        'description': row['description'],
                        'team_type': row['team_type'],
                        'settings': row['settings'] or {},
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(teams).encode())
                
            finally:
                await conn.close()
        except Exception as e:
            self.send_error(500, str(e))
    
    async def handle_teams_post(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                team_id = str(uuid.uuid4())
                row = await conn.fetchrow("""
                    INSERT INTO teams (id, organization_id, name, description, team_type, settings)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING 
                        id::text, organization_id::text, name, description,
                        team_type, settings, created_at::text, updated_at::text
                """, team_id, data['organization_id'], data['name'], 
                     data.get('description'), data.get('team_type', 'general'), json.dumps(data.get('settings', {})))
                
                result = {
                    'id': row['id'],
                    'organization_id': row['organization_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'team_type': row['team_type'],
                    'settings': row['settings'] or {},
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            finally:
                await conn.close()
        except Exception as e:
            self.send_error(500, str(e))
    
    def proxy_request(self):
        try:
            # Proxy to original API
            url = f"{ORIGINAL_API}{self.path}"
            
            if self.command == 'GET':
                response = requests.get(url)
            elif self.command == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length) if content_length > 0 else b''
                response = requests.post(url, data=post_data, 
                                       headers={'Content-Type': self.headers.get('Content-Type', 'application/json')})
            else:
                self.send_error(405, "Method not allowed")
                return
            
            self.send_response(response.status_code)
            self.send_header('Access-Control-Allow-Origin', '*')
            for header, value in response.headers.items():
                if header.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(header, value)
            self.end_headers()
            self.wfile.write(response.content)
            
        except Exception as e:
            self.send_error(500, str(e))

if __name__ == "__main__":
    server = HTTPServer(('localhost', PORT), ProxyHandler)
    print(f"Proxy server running on http://localhost:{PORT}")
    print(f"Proxying to {ORIGINAL_API} with hierarchy endpoints")
    server.serve_forever()