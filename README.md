# UO-News

## Development Set Up

Install the dependencies:

```bash
cd uo-news-api
uv pip install -e .
```

### Creating .env file

````bash
cp ./.environments/.env.example .env
````

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | API listen address |
| `API_PORT` | `8000` | API listen port |
| `API_RELOAD` | `false` | Enable auto-reload on code changes |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Running the API REST service

### Local

From the `uo-news-api/` directory:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

From the project root:

```bash
docker compose up --build
```

> [!INFO]
> Before running the API, be sure to add the `noticias_uniovi.json` file to the `uo-news-api/data/` directory. This file contains the news data that the API will read.
