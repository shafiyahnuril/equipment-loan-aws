"""Entry point aplikasi. FastAPI dibungkus Mangum supaya bisa berjalan di AWS Lambda."""

import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mangum import Mangum

from .repository import StorageError
from .routes import router

logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("equipment-loan")

app = FastAPI(
    title="Equipment Loan API",
    version="0.1.0",
    description="REST API untuk mencatat peminjaman alat laboratorium. Berjalan di AWS Lambda dengan DynamoDB (atau S3 sebagai cadangan).",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Catat setiap request dalam format JSON supaya mudah dibaca di CloudWatch Logs."""
    started = time.perf_counter()
    response = await call_next(request)
    context = request.scope.get("aws.context")
    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "durationMs": round((time.perf_counter() - started) * 1000, 1),
                "requestId": getattr(context, "aws_request_id", None),
            }
        )
    )
    return response


@app.exception_handler(StorageError)
async def storage_error_handler(request: Request, error: StorageError):
    logger.error(json.dumps({"event": "storage_error", "path": request.url.path, "error": str(error)}))
    return JSONResponse(
        status_code=500,
        content={"detail": "Terjadi kesalahan pada penyimpanan data"},
    )


app.include_router(router)

# Handler yang didaftarkan di Lambda: app.main.handler
handler = Mangum(app, lifespan="off")
