# LAND USE API

## Main info
This API is created to calculate the level of urbanization and renovation potential of land use zones.

## API methods
### /api/scenarios/{scenario_id}/renovation_potential
Endpoint for renovation potential calculation for given scenario ID
### /api/scenarios/{scenario_id}/urbanization_level
Endpoint for urbanization level calculation for given scenario ID
### /api/scenarios/{scenario_id}/context/renovation_potential
Endpoint for renovation potential calculation for context of given scenario ID
### /api/scenarios/{scenario_id}/context/urbanization_level
Endpoint for renovation potential calculation for context of given scenario ID
### /api/scenarios/{scenario_id}/landuse_percentages
Endpoint for getting land use percentages for a scenario.
## Indicators
### /api/indicators/{territory_id}/calculate_territory_urbanization
Endpoint for urbanization percentage indicator calculation for given territory ID
### /api/indicators/{territory_id}/calculate_area_indicator
Endpoint for area indicator calculation for given territory ID
### /api/indicators/{territory_id}/services_count_indicator
Endpoint for services counts indicators calculation and for given territory ID
### /api/indicators/{project_id}/calculate_project_area_indicator
Endpoint for services counts indicators calculation and for given project ID
## System
### /health_check/ping
Endpoint for application work ping
### /logs
Endpoint for getting logs

## Authentication

The API uses **Keycloak** bearer tokens. Every scenario/indicator endpoint requires an
`Authorization: Bearer <jwt>` header — the frontend passes its token, which is forwarded
verbatim to `urban_api` (which performs the actual authorization).

- **HTTP requests** — the token is taken from the incoming request and forwarded downstream.
- **Kafka / background path** — there is no frontend token, so the service obtains its own
  token from Keycloak via the `client_credentials` grant (using `AUTH_CLIENT_ID` /
  `AUTH_CLIENT_SECRET`).

Local signature verification is optional: with `AUTH_VERIFY=false` (default) the token is
accepted as-is and validated downstream by `urban_api`; with `AUTH_VERIFY=true` the RS256
signature, issuer and (optionally) audience are checked against the realm JWKS.

### Environment variables

| Variable | Description | Default |
| --- | --- | --- |
| `AUTH_SERVER_URL` | Keycloak realm base URL, e.g. `https://keycloak.../realms/<realm>` | — (required) |
| `AUTH_CLIENT_ID` | Service-account client id (used for the Kafka/background path) | — |
| `AUTH_CLIENT_SECRET` | Service-account client secret | — |
| `AUTH_VERIFY` | Verify the token signature locally via JWKS (`true`) or just forward it (`false`) | `false` |
| `AUTH_VERIFY_AUD` | Validate the `aud` claim when verifying | `true` |
| `AUTH_VALID_AUDIENCES` | Comma-separated list of accepted audiences | empty |
| `AUTH_JWKS_CACHE_TTL` | JWKS cache TTL, seconds | `600` |
| `AUTH_USER_CACHE_TTL` | Decoded-token cache TTL, seconds | `300` |
| `AUTH_USER_CACHE_SIZE` | Decoded-token cache size | `10000` |
| `AUTH_TIMEOUT_SECONDS` | Timeout for Keycloak (JWKS / token) requests, seconds | `5` |