from __future__ import annotations

from pydantic import BaseModel


class CognitoUserPool(BaseModel):
    """Cognito User Pool. cognito.describe_user_pool()"""

    Id: str | None = None
    Name: str | None = None
    Policies: dict | None = None
    LambdaConfig: dict | None = None
    Status: str | None = None
    LastModifiedDate: str | None = None
    CreationDate: str | None = None
    SchemaAttributes: list[dict] | None = None
    AutoVerifiedAttributes: list[str] | None = None
    AliasAttributes: list[str] | None = None
    UsernameAttributes: list[str] | None = None
    SmsVerificationMessage: str | None = None
    EmailVerificationMessage: str | None = None
    MfaConfiguration: str | None = None
    UserPoolTags: dict | None = None
    Arn: str | None = None
    AccountRecoverySetting: dict | None = None


class CognitoUser(BaseModel):
    """Cognito user record. cognito.admin_get_user() / list_users()"""

    Username: str | None = None
    UserAttributes: list[dict] | None = None
    UserCreateDate: str | None = None
    UserLastModifiedDate: str | None = None
    Enabled: bool | None = None
    UserStatus: str | None = None
    MFAOptions: list[dict] | None = None


class CognitoAuthRequest(BaseModel):
    """Initiate auth flow. cognito.initiate_auth()"""

    AuthFlow: str | None = None
    ClientId: str | None = None
    AuthParameters: dict | None = None
    UserPoolId: str | None = None


class CognitoAuthResponse(BaseModel):
    """Auth response with tokens. cognito.initiate_auth() result."""

    ChallengeName: str | None = None
    AuthenticationResult: dict | None = None
    ChallengeParameters: dict | None = None
    Session: str | None = None


class CognitoIdentityPool(BaseModel):
    """Cognito Identity Pool (federated identities). cognito-identity.describe_identity_pool()"""

    IdentityPoolId: str | None = None
    IdentityPoolName: str | None = None
    AllowUnauthenticatedIdentities: bool | None = None
    AllowClassicFlow: bool | None = None
    SupportedLoginProviders: dict | None = None
    DeveloperProviderName: str | None = None
    OpenIdConnectProviderARNs: list[str] | None = None
    CognitoIdentityProviders: list[dict] | None = None
    SamlProviderARNs: list[str] | None = None
    IdentityPoolTags: dict | None = None


class CognitoGetCredentialsResponse(BaseModel):
    """Temporary AWS credentials from Cognito Identity Pool. cognito-identity.get_credentials_for_identity()"""

    IdentityId: str | None = None
    Credentials: dict | None = None
