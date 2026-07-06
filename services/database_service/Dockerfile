# Use the pgvector-enabled PostgreSQL image as the base
FROM pgvector/pgvector:pg15

# Set environment variables
ENV POSTGRES_DB=ai_context
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=password

# Copy initialization scripts
COPY init-scripts/ /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD pg_isready -U postgres -d ai_context

# Use the default PostgreSQL entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["postgres"]