# mock-api

[![Quality](https://github.com/pfrest/mock-api/actions/workflows/quality.yml/badge.svg)](https://github.com/pfrest/mock-api/actions/workflows/quality.yml)
[![Release](https://github.com/pfrest/mock-api/actions/workflows/release.yml/badge.svg)](https://github.com/pfrest/mock-api/actions/workflows/release.yml)

A lightweight mock REST API service built with [Quart](https://quart.palletsprojects.com/).
Designed for testing—configure it with plain JSON files and a Docker container.

## How it works

Place `.json` files in a directory (default: `mocks/`).  Each filename encodes
the HTTP method and URL path:

```
<method>_<path>.json
```

> [!IMPORTANT]
> Use double-underscores to denote an actual underscore in the URL.

### Examples

| Filename                       | Route                    |
|--------------------------------|--------------------------|
| `get_api_users.json`           | `GET /api/users`         |
| `post_auth_login.json`         | `POST /auth/login`       |
| `get_api_user__profile.json`   | `GET /api/user_profile`  |
| `get_.json`                    | `GET /`                  |

### Mock file format

```json
{
    "status_code": 200,
    "body": { "users": [] },
    "headers": { "X-Custom-Header": "value" }
}
```

> [!NOTE]
> - All fields are optional. `status_code` defaults to `200`, `body` and `headers` default to `{}`.
> - `status_code` sets the status code returned by the mock-api when requests are received.
> - `headers` sets the response headers returned by the mock-api when requests are received.
> - `body` sets the response body return by the mock-api when requests are received.

## Authentication

Set `MOCK_API_AUTH_HEADERS` to a JSON object of header name/value pairs that every
request must supply:

```bash
MOCK_API_AUTH_HEADERS='{"Authorization": "Bearer my-token"}'
```

Leave it unset (or `{}`) to disable authentication.

## Running with Docker

```bash
docker run \
  -p 5000:5000 \
  -v "$(pwd)/my-mocks:/mocks" \
  -e MOCK_API_MOCKS_DIR=/mocks \
  -e MOCK_API_AUTH_HEADERS='{"Authorization": "Bearer test"}' \
  ghcr.io/pfrest/mock-api:latest
```

## Environment variables

| Variable                | Default  | Description                                           |
|-------------------------|----------|-------------------------------------------------------|
| `MOCK_API_MOCKS_DIR`    | `mocks`  | Directory containing mock JSON files                  |
| `MOCK_API_AUTH_HEADERS` | `{}`     | JSON object of required request headers (auth config) |

## Development

```bash
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
pylint app/ tests/
```

## Releases

Merges into `main` trigger the release workflow which uses
[Release Please](https://github.com/googleapis/release-please) to generate a
changelog from [Conventional Commits](https://www.conventionalcommits.org/) and
publish a Docker image to `ghcr.io`.
