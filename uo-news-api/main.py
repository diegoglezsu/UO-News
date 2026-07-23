import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config.logging import setup_logging
from config.settings import API_HOST, API_PORT, API_RELOAD
from api.routes import router

setup_logging()
logger = logging.getLogger("uo-news-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Indexing ChromaDB on startup...")

    yield

    logger.info("Shutting down service...")


app = FastAPI(
    title="UO-News API",
    description="API REST for querying news from the University of Oviedo indexed in ChromaDB.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=API_RELOAD)
