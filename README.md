# UO-News

## Get Started

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
| `JSON_FILE_NAME` | `noticias_uniovi.json` | Name of the JSON file containing news data |

### Running the API REST service

From the `uo-news-api/` directory:

- Local

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Docker

```bash
docker compose up --build
```

> [!IMPORTANT]
> Before running the API, be sure to add the `noticias_uniovi.json` file to the `uo-news-api/data/` directory. This file contains the news data that the API will read and it must have the correct structure.
