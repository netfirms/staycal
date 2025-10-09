# Stage 1: Build the application with dependencies
FROM python:3.10-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Create the final, lean image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-root user and group for the application
RUN addgroup --system appgroup && adduser --system --ingroup appgroup --no-create-home appuser

# Copy dependencies from the builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy the application source and entrypoint
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup entrypoint.sh ./

# Make the entrypoint script executable
RUN chmod +x ./entrypoint.sh

# Switch to the non-root user
USER appuser

ENV PORT=8000
EXPOSE 8000

# Set the entrypoint to our script
ENTRYPOINT ["./entrypoint.sh"]

# Use the shell form of CMD to allow for environment variable substitution.
# This string will be executed by the entrypoint script.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
