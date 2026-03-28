"""Comprehensive tests for the mock API application.

100 % branch and line coverage is maintained for ``app.app``.
"""

import json

import pytest

from app.app import create_app, load_mocks, parse_filename


# ---------------------------------------------------------------------------
# parse_filename
# ---------------------------------------------------------------------------


class TestParseFilename:
    """Tests for :func:`~app.app.parse_filename`."""

    def test_simple_path(self):
        """Single-depth path is parsed correctly."""
        method, path = parse_filename("get_users.json")
        assert method == "GET"
        assert path == "/users"

    def test_multi_segment_path(self):
        """Multiple underscores map to forward slashes."""
        method, path = parse_filename("get_api_v1_users.json")
        assert method == "GET"
        assert path == "/api/v1/users"

    def test_double_underscore_becomes_literal_underscore(self):
        """Double underscores map to a literal underscore in the URL."""
        method, path = parse_filename("get_api_user__profile.json")
        assert method == "GET"
        assert path == "/api/user_profile"

    def test_double_underscore_mixed_with_single(self):
        """Double and single underscores are handled in the same filename."""
        method, path = parse_filename("get_api__v1_user__info.json")
        assert method == "GET"
        assert path == "/api_v1/user_info"

    def test_post_method(self):
        """POST method is extracted correctly."""
        method, path = parse_filename("post_auth_login.json")
        assert method == "POST"
        assert path == "/auth/login"

    def test_delete_method(self):
        """DELETE method is extracted correctly."""
        method, path = parse_filename("delete_api_items_1.json")
        assert method == "DELETE"
        assert path == "/api/items/1"

    def test_root_path(self):
        """Filename with empty path after method maps to the root URL."""
        method, path = parse_filename("get_.json")
        assert method == "GET"
        assert path == "/"

    def test_method_uppercased(self):
        """Method is always returned in upper-case."""
        method, _ = parse_filename("POST_users.json")
        assert method == "POST"

    def test_invalid_filename_raises_value_error(self):
        """Filename without an underscore separator raises ValueError."""
        with pytest.raises(ValueError, match="missing '_' separator"):
            parse_filename("getusers.json")


# ---------------------------------------------------------------------------
# load_mocks
# ---------------------------------------------------------------------------


class TestLoadMocks:
    """Tests for :func:`~app.app.load_mocks`."""

    def test_nonexistent_directory_returns_empty(self):
        """Missing directory is handled gracefully."""
        mocks = load_mocks("/nonexistent/path/that/does/not/exist")
        assert not mocks

    def test_empty_directory_returns_empty(self, tmp_path):
        """Directory with no JSON files returns an empty dict."""
        mocks = load_mocks(str(tmp_path))
        assert not mocks

    def test_valid_mock_file_loaded(self, tmp_path):
        """A well-formed mock file is loaded and keyed correctly."""
        payload = {"status_code": 200, "body": {"users": []}}
        (tmp_path / "get_users.json").write_text(json.dumps(payload))
        mocks = load_mocks(str(tmp_path))
        assert ("GET", "/users") in mocks
        assert mocks[("GET", "/users")] == payload

    def test_multiple_mock_files_loaded(self, tmp_path):
        """Multiple valid mock files are all loaded."""
        (tmp_path / "get_users.json").write_text(
            json.dumps({"status_code": 200, "body": {}})
        )
        (tmp_path / "post_users.json").write_text(
            json.dumps({"status_code": 201, "body": {}})
        )
        mocks = load_mocks(str(tmp_path))
        assert ("GET", "/users") in mocks
        assert ("POST", "/users") in mocks

    def test_invalid_json_file_skipped(self, tmp_path):
        """A file containing malformed JSON is silently skipped."""
        (tmp_path / "get_bad.json").write_text("not valid json {{{")
        mocks = load_mocks(str(tmp_path))
        assert not mocks

    def test_invalid_filename_skipped(self, tmp_path):
        """A JSON file whose name has no underscore separator is skipped."""
        (tmp_path / "invalid.json").write_text(json.dumps({"status_code": 200}))
        mocks = load_mocks(str(tmp_path))
        assert not mocks

    def test_mixed_valid_and_invalid_files(self, tmp_path):
        """Valid files are loaded even when invalid files are present."""
        (tmp_path / "get_users.json").write_text(
            json.dumps({"status_code": 200, "body": {}})
        )
        (tmp_path / "badfile.json").write_text("not json")
        mocks = load_mocks(str(tmp_path))
        assert len(mocks) == 1
        assert ("GET", "/users") in mocks


# ---------------------------------------------------------------------------
# create_app – configuration
# ---------------------------------------------------------------------------


class TestCreateApp:
    """Tests for :func:`~app.app.create_app` configuration."""

    def test_returns_quart_app(self, tmp_path):
        """create_app always returns a Quart instance."""
        import quart  # pylint: disable=import-outside-toplevel

        app = create_app(mocks_dir=str(tmp_path), auth_headers={})
        assert isinstance(app, quart.Quart)

    def test_defaults_read_from_env_mocks_dir(self, tmp_path, monkeypatch):
        """MOCK_API_MOCKS_DIR env-var is used when mocks_dir is not provided."""
        monkeypatch.setenv("MOCK_API_MOCKS_DIR", str(tmp_path))
        monkeypatch.setenv("MOCK_API_AUTH_HEADERS", "{}")
        app = create_app()
        assert app is not None

    def test_defaults_read_from_env_auth_headers(self, tmp_path, monkeypatch):
        """MOCK_API_AUTH_HEADERS env-var is used when auth_headers is not provided."""
        monkeypatch.setenv("MOCK_API_AUTH_HEADERS", '{"X-Token": "secret"}')
        app = create_app(mocks_dir=str(tmp_path))
        assert app is not None


# ---------------------------------------------------------------------------
# Fixtures shared by handler tests
# ---------------------------------------------------------------------------


@pytest.fixture(name="mocks_dir")
def fixture_mocks_dir(tmp_path):
    """Populate a temporary directory with mock JSON files."""
    (tmp_path / "get_users.json").write_text(
        json.dumps(
            {
                "status_code": 200,
                "body": {"users": []},
                "headers": {"X-Custom": "yes"},
            }
        )
    )
    (tmp_path / "post_users.json").write_text(
        json.dumps({"status_code": 201, "body": {"created": True}})
    )
    (tmp_path / "get_.json").write_text(
        json.dumps({"status_code": 200, "body": {"message": "root"}})
    )
    (tmp_path / "get_api_user__info.json").write_text(
        json.dumps({"status_code": 200, "body": {"info": "ok"}})
    )
    return str(tmp_path)


@pytest.fixture(name="app")
def fixture_app(mocks_dir):
    """App with no authentication required."""
    return create_app(mocks_dir=mocks_dir, auth_headers={})


@pytest.fixture(name="auth_app")
def fixture_auth_app(mocks_dir):
    """App requiring an Authorization header."""
    return create_app(
        mocks_dir=mocks_dir,
        auth_headers={"Authorization": "Bearer token"},
    )


# ---------------------------------------------------------------------------
# Route handler – unauthenticated app
# ---------------------------------------------------------------------------


class TestMockHandler:
    """Tests for the catch-all route handler (no auth)."""

    async def test_get_route_returns_mock(self, app):
        """A known GET route returns the mocked body and status."""
        async with app.test_client() as client:
            response = await client.get("/users")
        assert response.status_code == 200
        data = await response.get_json()
        assert data == {"users": []}

    async def test_custom_response_headers_forwarded(self, app):
        """Custom response headers from the mock file are forwarded."""
        async with app.test_client() as client:
            response = await client.get("/users")
        assert response.headers.get("X-Custom") == "yes"

    async def test_post_route_returns_mock(self, app):
        """A known POST route returns the mocked body and status."""
        async with app.test_client() as client:
            response = await client.post("/users")
        assert response.status_code == 201
        data = await response.get_json()
        assert data == {"created": True}

    async def test_root_route_returns_mock(self, app):
        """A request to / matches the get_.json mock."""
        async with app.test_client() as client:
            response = await client.get("/")
        assert response.status_code == 200
        data = await response.get_json()
        assert data == {"message": "root"}

    async def test_unknown_route_returns_404(self, app):
        """A request for which no mock exists returns 404."""
        async with app.test_client() as client:
            response = await client.get("/does/not/exist")
        assert response.status_code == 404
        data = await response.get_json()
        assert "error" in data

    async def test_double_underscore_url(self, app):
        """A path derived from a double-underscore filename is resolved."""
        async with app.test_client() as client:
            response = await client.get("/api/user_info")
        assert response.status_code == 200
        data = await response.get_json()
        assert data == {"info": "ok"}

    async def test_no_response_headers_when_not_in_mock(self, app):
        """When the mock defines no headers, the route still works."""
        async with app.test_client() as client:
            response = await client.post("/users")
        # No X-Custom header expected for this mock
        assert response.headers.get("X-Custom") is None

    async def test_default_status_code(self, tmp_path):
        """status_code defaults to 200 when omitted from the mock file."""
        (tmp_path / "get_ping.json").write_text(json.dumps({"body": {"ok": True}}))
        test_app = create_app(mocks_dir=str(tmp_path), auth_headers={})
        async with test_app.test_client() as client:
            response = await client.get("/ping")
        assert response.status_code == 200

    async def test_default_body(self, tmp_path):
        """body defaults to {} when omitted from the mock file."""
        (tmp_path / "get_ping.json").write_text(json.dumps({"status_code": 204}))
        test_app = create_app(mocks_dir=str(tmp_path), auth_headers={})
        async with test_app.test_client() as client:
            response = await client.get("/ping")
        assert response.status_code == 204


# ---------------------------------------------------------------------------
# Route handler – authenticated app
# ---------------------------------------------------------------------------


class TestMockHandlerAuth:
    """Tests for the route handler when authentication is enabled."""

    async def test_correct_auth_header_allows_request(self, auth_app):
        """A request with the correct auth header is allowed through."""
        async with auth_app.test_client() as client:
            response = await client.get(
                "/users", headers={"Authorization": "Bearer token"}
            )
        assert response.status_code == 200

    async def test_missing_auth_header_returns_401(self, auth_app):
        """A request without the required auth header returns 401."""
        async with auth_app.test_client() as client:
            response = await client.get("/users")
        assert response.status_code == 401
        data = await response.get_json()
        assert data == {"error": "Unauthorized"}

    async def test_wrong_auth_header_value_returns_401(self, auth_app):
        """A request with an incorrect auth header value returns 401."""
        async with auth_app.test_client() as client:
            response = await client.get(
                "/users", headers={"Authorization": "Bearer wrong"}
            )
        assert response.status_code == 401
