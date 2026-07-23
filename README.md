# UO-News

## Development Set Up

Install the dependencies:

```bash
uv pip install -e .
```

Levantar el servidor web:

```bash
uvicorn src.main:app --reload  --port 8000 --host 0.0.0.0
```
