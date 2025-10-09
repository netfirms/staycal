# Use a single-stage build for simplicity and robustness
FROM python:3.10-slim

# Add a label to force a rebuild and bust the cache
LABEL build_date="2024-07-31"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install all dependencies from requirements.txt into the global site-packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and group for the application
RUN addgroup --system appgroup && adduser --system --ingroup appgroup --no-create-home appuser

# Copy the application source and entrypoint script
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup entrypoint.sh ./

# Make the entrypoint script executable
RUN chmod +x ./entrypoint.sh

# Switch to the non-root user for security
USER appuser

ENV PORT=8000
EXPOSE 8000

# Set the entrypoint to our script
ENTRYPOINT ["./entrypoint.sh"]

# The command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
