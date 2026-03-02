"""Google Firebase SDK schemas.

Covers Firebase Realtime Database, Firestore, Firebase Auth, Firebase Cloud
Messaging (FCM), and Firebase Storage. Maps to firebase_admin SDK and REST APIs.

Firebase products:
- Realtime Database: firebase_admin.db - JSON tree, WebSocket streaming
- Firestore: firebase_admin.firestore / google.cloud.firestore_v1 - document/collection NoSQL
- Firebase Auth: firebase_admin.auth - user management, custom tokens, ID token verification
- FCM: firebase_admin.messaging - push notifications to mobile/web clients
- Firebase Storage: firebase_admin.storage - wraps GCS bucket
"""

from __future__ import annotations

from pydantic import BaseModel

from unified_api_contracts.shared import ErrorAction


class FirestoreDocument(BaseModel):
    """Firestore document snapshot. Maps to google.cloud.firestore_v1.DocumentSnapshot.

    Fields are stored as Firestore value types; this schema captures common Python
    representations after deserialization.
    Endpoint: GET projects/{p}/databases/{db}/documents/{collection}/{doc_id}
    """

    name: str | None = None
    fields: dict | None = None
    create_time: str | None = None
    update_time: str | None = None


class FirestoreQuery(BaseModel):
    """Firestore structured query parameters.

    Used with collection.where(), order_by(), limit() chains via SDK.
    REST: POST documents:runQuery
    """

    collection: str | None = None
    filters: list[dict] | None = None
    order_by: list[dict] | None = None
    limit: int | None = None
    offset: int | None = None
    start_after: dict | None = None


class FirestoreWriteResult(BaseModel):
    """Result of a Firestore write (set/update/delete).

    Endpoint: PATCH documents/{path}
    """

    update_time: str | None = None
    document_id: str | None = None
    write_time: str | None = None


class FirestoreBatchWriteRequest(BaseModel):
    """Batch write (up to 500 operations atomically).

    REST: POST documents:batchWrite
    """

    writes: list[dict] | None = None


class RealtimeDbEntry(BaseModel):
    """Firebase Realtime Database entry (JSON value at a path).

    SDK: db.reference(path).get() / .set() / .update()
    REST: GET/PUT/PATCH/POST https://{project}.firebaseio.com/{path}.json
    Realtime updates via Server-Sent Events (?stream=true) or SDK listener.
    """

    path: str | None = None
    data: dict | str | list | float | bool | None = None
    etag: str | None = None


class FirebaseAuthUser(BaseModel):
    """Firebase Auth user record. Maps to firebase_admin.auth.UserRecord.

    SDK: auth.get_user(uid) / auth.get_user_by_email(email)
    """

    uid: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    display_name: str | None = None
    phone_number: str | None = None
    photo_url: str | None = None
    disabled: bool | None = None
    provider_data: list[dict] | None = None
    custom_claims: dict | None = None
    tokens_valid_after_time: str | None = None
    creation_timestamp: int | None = None
    last_sign_in_timestamp: int | None = None
    last_refresh_timestamp: int | None = None
    tenant_id: str | None = None


class FirebaseAuthToken(BaseModel):
    """Firebase ID token payload (decoded). Maps to auth.verify_id_token() result.

    Used to authenticate requests from Firebase client SDKs.
    """

    uid: str | None = None
    iss: str | None = None
    aud: str | None = None
    iat: int | None = None
    exp: int | None = None
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    picture: str | None = None
    firebase: dict | None = None


class FirebaseCustomToken(BaseModel):
    """Custom token created by firebase_admin.auth.create_custom_token().

    Used for server-to-client auth flows (backend mints token, client signs in).
    """

    token: str | None = None
    uid: str | None = None
    additional_claims: dict | None = None


class FirebaseCreateUserRequest(BaseModel):
    """Request to create a Firebase Auth user. auth.create_user(**params)."""

    email: str | None = None
    email_verified: bool | None = None
    password: str | None = None
    display_name: str | None = None
    phone_number: str | None = None
    photo_url: str | None = None
    disabled: bool | None = None
    uid: str | None = None


class FcmMessage(BaseModel):
    """Firebase Cloud Messaging message payload.

    SDK: messaging.send(Message(...))
    REST: POST https://fcm.googleapis.com/v1/projects/{project}/messages:send
    """

    token: str | None = None
    topic: str | None = None
    condition: str | None = None
    notification: dict | None = None
    data: dict[str, str] | None = None
    android: dict | None = None
    apns: dict | None = None
    webpush: dict | None = None
    fcm_options: dict | None = None


class FcmSendResponse(BaseModel):
    """Response from messaging.send() or batch send.

    SDK: messaging.send_multicast() returns BatchResponse.
    """

    message_id: str | None = None
    success_count: int | None = None
    failure_count: int | None = None
    responses: list[dict] | None = None


class FirebaseStorageObject(BaseModel):
    """Firebase Storage object metadata (wraps GCS via firebase_admin.storage).

    bucket = storage.bucket() - returns google.cloud.storage.Bucket
    """

    name: str | None = None
    bucket: str | None = None
    content_type: str | None = None
    size: int | None = None
    time_created: str | None = None
    updated: str | None = None
    download_url: str | None = None
    metadata: dict[str, str] | None = None


class FirebaseError(BaseModel):
    """Firebase Admin SDK / REST API error."""

    code: str | None = None
    message: str | None = None
    http_status: int | None = None

    @classmethod
    def classify(cls, code: str | None = None, http_status: int | None = None):
        if http_status == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        if http_status is not None and http_status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
