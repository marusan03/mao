# MAO API Quick Start

## Installation

```bash
# Install MAO with API dependencies
uv pip install -e .

# Or with pip
pip install -e .
```

## Start API Server

```bash
# Using the CLI command
mao-api

# Server runs at: http://localhost:8000
# API docs: http://localhost:8000/docs
```

## Test the API

```bash
# In a new terminal, run the test script
python examples/test_contact_api.py
```

## Basic Usage

### Submit a Contact Form

```bash
curl -X POST http://localhost:8000/api/v1/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "message": "This is a test message from the contact form."
  }'
```

### Get a Submission

```bash
curl http://localhost:8000/api/v1/contact/cf_20260202_123456_abc123
```

### List All Submissions

```bash
curl http://localhost:8000/api/v1/contact
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Interactive Documentation

Visit http://localhost:8000/docs for:
- Interactive API playground
- Complete endpoint documentation
- Request/response schemas
- Try it out directly in your browser

## Storage Location

Submissions are stored in:
```
.mao/contact_forms/
├── cf_20260202_123456_abc123.json
├── cf_20260202_123455_def456.json
└── ...
```

## Python Client Example

```python
import httpx
import asyncio

async def submit_form():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/contact",
            json={
                "name": "John Doe",
                "email": "john.doe@example.com",
                "message": "Hello from Python!"
            }
        )
        print(response.json())

asyncio.run(submit_form())
```

## Validation Rules

- **Name**: 2-100 characters, letters/numbers/spaces/hyphens/apostrophes/periods
- **Email**: Valid email format
- **Message**: 10-5000 characters

## More Information

- Full documentation: `mao/api/README.md`
- Implementation details: `mao/api/IMPLEMENTATION_SUMMARY.md`
- Test examples: `examples/test_contact_api.py`

## Troubleshooting

**Server won't start?**
- Check if port 8000 is already in use
- Try: `uvicorn mao.api.app:app --port 8001`

**Module not found errors?**
- Install dependencies: `uv pip install -e .`
- Activate virtual environment if needed

**API not responding?**
- Verify server is running: `curl http://localhost:8000/health`
- Check logs for errors
