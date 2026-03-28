"""Mock REST API service built with Quart.

JSON files inside *MOCKS_DIR* define the responses.  The file name encodes
the HTTP method and URL path::

    <method>_<path>.json

Path encoding rules
-------------------
* A single underscore ``_`` in the path segment becomes a forward slash ``/``.
* A double underscore ``__`` becomes a literal underscore ``_``.

Examples::

    get_api_users.json          → GET  /api/users
    post_auth_login.json        → POST /auth/login
    get_api_user__profile.json  → GET  /api/user_profile
    get_.json                   → GET  /

Mock file format
----------------
.. code-block:: json

    {
        "status_code": 200,
        "body": {"key": "value"},
        "headers": {"X-Custom-Header": "custom-value"}
    }

All fields are optional; defaults are ``status_code=200``, ``body={}``,
``headers={}``.

Authentication
--------------
Set the ``MOCK_API_AUTH_HEADERS`` environment variable to a JSON object whose keys
are the required request header names and whose values are the expected
header values.  An empty object (the default) disables authentication.

Example::

    MOCK_API_AUTH_HEADERS='{"Authorization": "Bearer my-token"}'
"""

import json
import os
from pathlib import Path
from typing import Optional

import quart
from quart import request

# Placeholder used internally while translating double-underscores.
_PLACEHOLDER = "\x00"

# HTTP methods exposed by every route.
HTTP_METHODS = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]


def parse_filename(filename: str) -> tuple:
    """Parse a mock JSON filename into an HTTP method and URL path.

    Args:
        filename: Mock JSON filename, e.g. ``"get_api_users.json"``.

    Returns:
        ``(method, path)`` tuple, e.g. ``("GET", "/api/users")``.

    Raises:
        ValueError: If *filename* contains no underscore separator.
    """
    stem = Path(filename).stem
    if "_" not in stem:
        raise ValueError(
            f"Invalid mock filename '{filename}': missing '_' separator"
        )
    method, _, path_part = stem.partition("_")
    # Protect double-underscores before converting singles to slashes.
    path_part = path_part.replace("__", _PLACEHOLDER)
    path_part = path_part.replace("_", "/")
    path_part = path_part.replace(_PLACEHOLDER, "_")
    return method.upper(), "/" + path_part


def load_mocks(mocks_dir: str) -> dict:
    """Load all mock JSON files from *mocks_dir*.

    Files with invalid names or malformed JSON are silently skipped.

    Args:
        mocks_dir: Path to the directory containing mock ``*.json`` files.

    Returns:
        Mapping of ``(method, path)`` tuples to mock response dicts.
    """
    mocks: dict = {}
    mocks_path = Path(mocks_dir)
    if not mocks_path.exists():
        return mocks
    for mock_file in sorted(mocks_path.glob("*.json")):
        try:
            method, path = parse_filename(mock_file.name)
            with open(mock_file, encoding="utf-8") as handle:
                data = json.load(handle)
            mocks[(method, path)] = data
        except (json.JSONDecodeError, ValueError):
            pass
    return mocks


def create_app(
    mocks_dir: Optional[str] = None,
    auth_headers: Optional[dict] = None,
) -> quart.Quart:
    """Create and configure the Quart application.

    Args:
        mocks_dir: Directory containing mock JSON files.  Defaults to the
            ``MOCK_API_MOCKS_DIR`` environment variable, falling back to ``"mocks"``.
        auth_headers: Request headers required for authentication.  Pass an
            empty dict (``{}``) to disable auth.  Defaults to the
            ``MOCK_API_AUTH_HEADERS`` environment variable (parsed as JSON), falling
            back to ``{}``.

    Returns:
        Configured :class:`quart.Quart` application instance.
    """
    if mocks_dir is None:
        mocks_dir = os.environ.get("MOCK_API_MOCKS_DIR", "mocks")
    if auth_headers is None:
        auth_headers = json.loads(os.environ.get("MOCK_API_AUTH_HEADERS", "{}"))

    app = quart.Quart(__name__)
    mocks = load_mocks(mocks_dir)

    async def mock_handler(path: str = ""):
        """Handle all incoming mock API requests."""
        if auth_headers:
            for header, expected in auth_headers.items():
                if request.headers.get(header) != expected:
                    return quart.jsonify({"error": "Unauthorized"}), 401

        method = request.method
        url = "/" + path if path else "/"
        mock_key = (method, url)

        if mock_key not in mocks:
            return (
                quart.jsonify({"error": f"No mock found for {method} {url}"}),
                404,
            )

        mock_data = mocks[mock_key]
        status_code = mock_data.get("status_code", 200)
        body = mock_data.get("body", {})
        response_headers = mock_data.get("headers", {})

        response = await quart.make_response(quart.jsonify(body), status_code)
        for header_name, header_value in response_headers.items():
            response.headers[header_name] = header_value

        return response

    app.add_url_rule(
        "/",
        endpoint="mock_root",
        view_func=mock_handler,
        methods=HTTP_METHODS,
        defaults={"path": ""},
    )
    app.add_url_rule(
        "/<path:path>",
        endpoint="mock_path",
        view_func=mock_handler,
        methods=HTTP_METHODS,
    )

    return app
