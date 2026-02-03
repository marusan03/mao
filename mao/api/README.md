# MAO API

This module provides HTTP API endpoints for external integrations with the MAO system.

## Features

- **Contact Form API**: Accept and store contact form submissions
- **Input Validation**: Automatic validation using Pydantic models
- **Error Handling**: Comprehensive error responses with appropriate status codes
- **Storage**: File-based storage in `.mao/contact_forms/` directory
- **Interactive Documentation**: Auto-generated API docs at `/docs`

## Installation

The API dependencies are included in MAO by default. To install API-specific dependencies:

```bash
# Install with API dependencies
pip install -e ".[api]"

# Or if using uv
uv pip install -e ".[api]"
```

## Usage

### Starting the API Server

```bash
# Using the CLI command
mao-api

# Or run directly with Python
python -m mao.api.app

# Or with uvicorn for more control
uvicorn mao.api.app:app --host 0.0.0.0 --port 8000 --reload
```

The API server will start on `http://localhost:8000` by default.

### API Documentation

Once the server is running, visit:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## Endpoints

### Root

**GET /**

Returns basic API information.

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "name": "MAO API",
  "version": "0.2.1",
  "description": "Multi-Agent Orchestrator API",
  "docs": "/docs",
  "openapi": "/openapi.json"
}
```

### Health Check

**GET /health**

Check if the API is running.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.2.1"
}
```

### Contact Form

#### Submit Contact Form

**POST /api/v1/contact**

Submit a contact form with name, email, and message.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "message": "I would like to inquire about your services..."
}
```

**Validation Rules:**
- `name`: 2-100 characters, alphanumeric with spaces, hyphens, apostrophes, and periods
- `email`: Valid email address format
- `message`: 10-5000 characters, non-empty after trimming whitespace

**Success Response (201 Created):**
```json
{
  "status": "success",
  "message": "Contact form submitted successfully",
  "submission_id": "cf_20260202_123456_abc123",
  "timestamp": "2026-02-02T12:34:56.789123"
}
```

**Error Response (400 Bad Request):**
```json
{
  "status": "error",
  "message": "Validation failed: name cannot be empty",
  "submission_id": null,
  "timestamp": "2026-02-02T12:34:56.789123"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "message": "This is a test message."
  }'
```

#### Get Contact Form by ID

**GET /api/v1/contact/{submission_id}**

Retrieve a specific contact form submission by its ID.

**Success Response (200 OK):**
```json
{
  "submission_id": "cf_20260202_123456_abc123",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "message": "This is a test message.",
  "submitted_at": "2026-02-02T12:34:56.789123",
  "ip_address": "192.168.1.1"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Contact form submission cf_20260202_123456_abc123 not found"
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/contact/cf_20260202_123456_abc123
```

#### List All Contact Forms

**GET /api/v1/contact**

List all contact form submissions (sorted by submission time, newest first).

**Note:** In production, consider adding pagination and authentication to protect this endpoint.

**Success Response (200 OK):**
```json
[
  {
    "submission_id": "cf_20260202_123456_abc123",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "message": "This is a test message.",
    "submitted_at": "2026-02-02T12:34:56.789123",
    "ip_address": "192.168.1.1"
  },
  {
    "submission_id": "cf_20260202_123455_def456",
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "message": "Another test message.",
    "submitted_at": "2026-02-02T12:34:55.123456",
    "ip_address": "192.168.1.2"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/v1/contact
```

## Testing

A test script is provided to verify the API functionality:

```bash
# Start the API server in one terminal
mao-api

# Run the test script in another terminal
python examples/test_contact_api.py
```

The test script will:
1. Check the health endpoint
2. Submit valid contact forms
3. Retrieve submissions by ID
4. List all submissions
5. Test validation errors (missing fields, invalid email, etc.)

## Storage

Contact form submissions are stored in the `.mao/contact_forms/` directory as JSON files. Each submission is stored with its unique ID as the filename:

```
.mao/
└── contact_forms/
    ├── cf_20260202_123456_abc123.json
    ├── cf_20260202_123455_def456.json
    └── ...
```

Example stored submission:
```json
{
  "submission_id": "cf_20260202_123456_abc123",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "message": "This is a test message.",
  "submitted_at": "2026-02-02T12:34:56.789123",
  "ip_address": "192.168.1.1"
}
```

## Architecture

### Components

- **`app.py`**: FastAPI application factory and configuration
- **`contact.py`**: Contact form API endpoint implementation
- **`models.py`**: Pydantic models for request/response validation
- **`storage.py`**: Storage backends (file-based and in-memory)

### Storage Backends

Two storage backends are provided:

1. **FileStorageBackend** (default): Stores submissions as JSON files
2. **InMemoryStorageBackend**: Stores submissions in memory (for testing)

To use a different backend, modify the `storage` initialization in `contact.py`:

```python
from mao.api.storage import InMemoryStorageBackend

storage = InMemoryStorageBackend()
```

## Production Considerations

When deploying to production, consider:

1. **Rate Limiting**: Add rate limiting to prevent abuse
   ```bash
   pip install slowapi
   ```

2. **Authentication**: Protect the list and get endpoints
   ```python
   from fastapi.security import HTTPBasic
   ```

3. **CORS**: Configure allowed origins appropriately
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

4. **HTTPS**: Use a reverse proxy (nginx, Caddy) with SSL
   ```bash
   uvicorn mao.api.app:app --host 127.0.0.1 --port 8000
   ```

5. **Monitoring**: Add logging and monitoring
   ```bash
   pip install sentry-sdk
   ```

6. **Database**: Consider using a database instead of file storage
   ```bash
   pip install sqlalchemy asyncpg
   ```

7. **Pagination**: Add pagination to the list endpoint
   ```python
   @router.get("/contact")
   async def list_contact_forms(skip: int = 0, limit: int = 100):
       ...
   ```

## Examples

### Python Client

```python
import httpx

async def submit_contact_form():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/contact",
            json={
                "name": "John Doe",
                "email": "john.doe@example.com",
                "message": "Hello from Python!"
            }
        )
        return response.json()
```

### JavaScript Client

```javascript
async function submitContactForm() {
  const response = await fetch('http://localhost:8000/api/v1/contact', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: 'John Doe',
      email: 'john.doe@example.com',
      message: 'Hello from JavaScript!'
    })
  });

  return await response.json();
}
```

### cURL

```bash
# Submit a contact form
curl -X POST http://localhost:8000/api/v1/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "message": "Hello from cURL!"
  }'

# Get a specific submission
curl http://localhost:8000/api/v1/contact/cf_20260202_123456_abc123

# List all submissions
curl http://localhost:8000/api/v1/contact
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the test script
python examples/test_contact_api.py
```

### Code Quality

```bash
# Format code
black mao/api/

# Lint code
ruff check mao/api/

# Type checking
mypy mao/api/
```

## License

MIT
