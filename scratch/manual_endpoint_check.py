from fastapi.testclient import TestClient
from backend.app.api.main import app
client = TestClient(app)
print('GET / ->', client.get('/').status_code, client.get('/').json())
print('GET /health ->', client.get('/health').status_code, client.get('/health').json())
print('GET /docs ->', client.get('/docs').status_code)
print('GET /openapi.json ->', client.get('/openapi.json').status_code)
