"""Google OAuth2 and service account credential schemas.

Covers:
- Google OAuth2 authorization flow (web/server/device)
- Service account key-based credentials
- Workload Identity Federation (keyless auth for CI/CD)
- ID token / access token management
- Domain-wide delegation (DWD)

Relevant libraries: google-auth, google-auth-oauthlib, google-auth-httplib2
"""

from __future__ import annotations

from pydantic import BaseModel

from unified_api_contracts import ErrorAction


class OAuth2TokenResponse(BaseModel):
    """OAuth2 token response from https://oauth2.googleapis.com/token.

    Used for authorization code flow, refresh token flow, and service account JWT exchange.
    """

    access_token: str | None = None
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    token_type: str | None = None
    id_token: str | None = None


class OAuth2TokenIntrospect(BaseModel):
    """Token introspection response from https://oauth2.googleapis.com/tokeninfo.

    Use GET ?access_token=... or ?id_token=... to inspect token validity.
    """

    azp: str | None = None
    aud: str | None = None
    sub: str | None = None
    scope: str | None = None
    exp: str | None = None
    expires_in: str | None = None
    email: str | None = None
    email_verified: str | None = None
    access_type: str | None = None
    error: str | None = None
    error_description: str | None = None


class ServiceAccountCredential(BaseModel):
    """Service account key file structure (JSON key file).

    Generated via: gcloud iam service-accounts keys create key.json --iam-account=SA
    Used as GOOGLE_APPLICATION_CREDENTIALS env var or firebase_admin.credentials.Certificate.
    """

    type: str = "service_account"
    project_id: str | None = None
    private_key_id: str | None = None
    private_key: str | None = None
    client_email: str | None = None
    client_id: str | None = None
    auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url: str | None = None
    client_x509_cert_url: str | None = None
    universe_domain: str = "googleapis.com"


class OAuth2AuthorizationRequest(BaseModel):
    """Parameters for building the OAuth2 authorization URL.

    Endpoint: GET https://accounts.google.com/o/oauth2/v2/auth
    Used for web/installed application flow (user consent screen).
    """

    client_id: str | None = None
    redirect_uri: str | None = None
    response_type: str = "code"
    scope: str | None = None
    access_type: str = "offline"
    state: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    include_granted_scopes: str | None = None
    prompt: str | None = None


class OAuth2TokenRequest(BaseModel):
    """Token exchange request to https://oauth2.googleapis.com/token."""

    grant_type: str | None = None
    code: str | None = None
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    assertion: str | None = None


class WorkloadIdentityCredential(BaseModel):
    """Workload Identity Federation credential configuration.

    Allows workloads outside GCP (GitHub Actions, AWS, Azure) to authenticate
    as a service account without a key file.
    Config file: workload_identity_federation_config.json
    Endpoint: https://sts.googleapis.com/v1/token (token exchange)
    """

    type: str = "external_account"
    audience: str | None = None
    subject_token_type: str | None = None
    token_url: str = "https://sts.googleapis.com/v1/token"
    credential_source: dict[str, object] | None = None
    service_account_impersonation_url: str | None = None
    service_account_impersonation: dict[str, object] | None = None
    scopes: list[str] | None = None


class OidcToken(BaseModel):
    """OIDC ID token (Google-issued). Verified via google.oauth2.id_token.verify_oauth2_token().

    Used for Cloud Run auth, service-to-service calls, and Firebase Auth.
    """

    iss: str | None = None
    sub: str | None = None
    aud: str | None = None
    iat: int | None = None
    exp: int | None = None
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    hd: str | None = None


class OAuth2Error(BaseModel):
    """OAuth2 / token endpoint error response."""

    error: str | None = None
    error_description: str | None = None
    error_uri: str | None = None

    @classmethod
    def classify(cls, error: str | None = None, http_status: int | None = None):
        if error in ("invalid_grant", "token_expired"):
            return ErrorAction.FAIL_HARD
        if http_status == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
