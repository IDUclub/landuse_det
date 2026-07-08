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

The API uses Keycloak bearer tokens. For HTTP requests, the incoming
`Authorization: Bearer <jwt>` header is forwarded to `urban_api`.

For Kafka and other background flows there is no incoming frontend token, so the
service obtains a Keycloak service token via the `client_credentials` grant.

### Environment variables

| Variable | Description | Default |
| --- | --- | --- |
| `KEYCLOAK_URL` | Keycloak base URL | - (required) |
| `KEYCLOAK_REALM` | Keycloak realm | - (required) |
| `KEYCLOAK_CLIENT_ID` | Service-account client id | - (required) |
| `KEYCLOAK_CLIENT_SECRET` | Service-account client secret | - (required) |
