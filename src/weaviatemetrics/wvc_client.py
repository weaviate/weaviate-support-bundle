import os
import weaviate
from loguru import logger
from typing import Dict, Any
from dotenv import load_dotenv



load_dotenv()


def make_connection() -> weaviate.Client:
    """Establish connection to Weaviate cluster."""
    try:
        APIKEY = os.getenv("AUTH_API_KEY")
        OIDC_USERNAME = os.getenv("OIDC_USERNAME")
        OIDC_PASSWORD = os.getenv("OIDC_PASSWORD")
        OIDC_SCOPES = os.getenv("OIDC_SCOPES").split(",") if os.getenv("OIDC_SCOPES") else None
        if APIKEY:
            auth_credentials = weaviate.auth.AuthApiKey(api_key=APIKEY)
        elif OIDC_USERNAME and OIDC_PASSWORD:
            auth_credentials = weaviate.auth.OidcAuth(
                username=OIDC_USERNAME,
                password=OIDC_PASSWORD,
                scope=OIDC_SCOPES
            )
        else:
            auth_credentials = None
        client = weaviate.connect_to_custom(
            http_host=os.getenv("WEAVIATE_HTTP_HOST"),
            http_port=int(os.getenv("WEAVIATE_HTTP_PORT", 80)),
            http_secure=os.getenv("WEAVIATE_HTTP_SECURE", "False").lower() == "true",
            grpc_host=os.getenv("WEAVIATE_GRPC_HOST"),
            grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", 50051)),
            grpc_secure=os.getenv("WEAVIATE_GRPC_SECURE", "False").lower() == "true",
            auth_credentials=auth_credentials
        )

        if client.is_ready():
            logger.info("Successfully connected to Weaviate cluster.")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Weaviate: {e}", exc_info=True)
        raise
