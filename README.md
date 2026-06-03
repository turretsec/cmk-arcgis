# Checkmk ArcGIS Enterprise Plugin

A Checkmk special agent for monitoring ArcGIS Enterprise deployments. The agent authenticates to an ArcGIS Portal, collects Portal and federated Server data via the ArcGIS REST Admin API, and emits piggyback sections for federated Server hosts.

---

## How it works

The special agent runs against a single Checkmk host representing the ArcGIS Portal. In deployments with a single Portal instance, it's recommended that the host be the machine running ArcGIS Portal. In other cases such as HA deployments, it's recommended to use a host checking the Portal URL itself. It:

1. Authenticates to Portal and collects Portal-level data (health, indexer, federation, license, log settings).
2. Retrieves the list of federated ArcGIS Servers from Portal.
3. Authenticates to each federated Server and collects server-level data (machines, services, datastores, license, log settings).
4. Emits Portal data as direct agent sections on the Portal host.
5. Emits Server data as piggyback sections targeting the corresponding Checkmk host for each federated Server.

```
Portal host (special agent runs here)
├── arcgis_portal_health
├── arcgis_portal_indexer
├── arcgis_portal_federation
├── arcgis_portal_license
├── arcgis_portal_log_settings
└── arcgis_collection_status

Federated Server hosts (piggyback)
├── arcgis_server_machines
├── arcgis_services
├── arcgis_registered_datastore_validation
├── arcgis_managed_datastore_validation
├── arcgis_server_license
└── arcgis_server_log_settings
```

Portal machine health data is also emitted per-machine. In a multi-machine Portal deployment, each machine's health section is sent as piggyback to its corresponding Checkmk host. In a single-machine deployment, the section goes directly to the Portal host.

---

## Requirements

- Checkmk 2.x (modern plug-in API)
- ArcGIS Enterprise with at least one Portal and one or more federated Servers
- An ArcGIS administrator account with access to Portal and Server admin endpoints
- A Checkmk host for the Portal
- Checkmk hosts for each federated ArcGIS Server machine (to receive piggyback services)

---

## Installation

### GUI

1. Go to **Setup -> Maintenance -> Extension packages**.
2. Upload the `.mkp` file and enable it.
3. Activate changes.

### Command line

```bash
mkp add arcgis-enterprise-<version>.mkp
mkp enable arcgis-enterprise <version>
cmk -R
```

Validate after installation:

```bash
cmk-validate-plugins
```

---

## Setup

1. Add a Checkmk host for the ArcGIS Portal.
2. Add Checkmk hosts for each federated ArcGIS Server machine.
3. Store the ArcGIS admin password in the Checkmk password store (**Setup -> Passwords**).
4. Create a special agent rule under **Setup -> VM, cloud, container -> ArcGIS Enterprise**, assigned to the Portal host.
5. Run service discovery on the Portal host and on each federated Server host.

---

## Special agent configuration

| Parameter | Description | Default |
|---|---|---|
| Portal URL | Base URL of your Portal, e.g. `https://gis.example.org/portal` | required |
| Username | ArcGIS admin username | required |
| Password | Password from the Checkmk password store | required |
| Verify SSL | Verify TLS certificates | enabled |
| Token expiry | How long generated tokens are valid (minutes) | 60 |

### Collection scope

Each collection area can be individually disabled. Disabled collections produce no agent output and do not generate warnings in the Collection Status service.

| Collection | What it collects |
|---|---|
| Portal health | Portal machine ready/not-ready state |
| Portal indexer | Index vs database count per index type; sync status |
| Portal federation validation | Status of each federated server and overall federation health |
| Portal license | Member usage and license item expiration |
| Portal log settings | Log level and log retention |
| Server machines | Configured and realtime state per server machine |
| Server services | Configured and realtime state per published service |
| Registered datastores | Validation status of registered (external) datastores |
| Managed datastores | Validation status of managed (internal) datastores |
| Server license | Edition, level, extension, and feature license info |
| Server log settings | Log level and log retention |

### Cache intervals

Section caching reduces how often expensive or slow collections run. Set to `0` to disable caching for a collection.

| Collection | Default cache |
|---|---|
| Portal federation validation | 300 s |
| Portal license | 3600 s |
| Portal log settings | 3600 s |
| Server machines | 300 s |
| Registered datastore validation | 900 s |
| Managed datastore validation | 900 s |
| Server license | 3600 s |
| Server log settings | 3600 s |

### Federated server filtering

Use regular expressions to limit which federated Servers are collected. Patterns are matched against the server name, URL, and admin URL. Exclude patterns take priority over include patterns.

Example: collect only servers with `/server` in their URL:
```
/server
```

Example: exclude image servers:
```
/image
```

---

## Discovered services

### Portal host

| Service | Description |
|---|---|
| `ArcGIS Portal Health` | Ready/not-ready state of each Portal machine |
| `ArcGIS Portal Index <name>` | Per-index database count vs index count (users, groups, items) |
| `ArcGIS Portal Index Sync` | Overall index sync health |
| `ArcGIS Federated Server <admin_url>` | Per-server federation validation status |
| `ArcGIS Portal Federation Status` | Overall federation validation status |
| `ArcGIS Portal License summary` | Total registered member count and Portal version |
| `ArcGIS Portal License <kind> <id>` | Per-item license usage percentage and expiration |
| `ArcGIS Portal Log Settings` | Log level and retention policy |
| `ArcGIS Collection Status` | Errors and warnings encountered during agent collection |

### Federated Server hosts (piggyback)

| Service | Description |
|---|---|
| `ArcGIS Server Machine <name>` | Configured and realtime state of each server machine |
| `ArcGIS Service <folder/name.type>` | Configured and realtime state of each published service |
| `ArcGIS Registered Datastore <path>` | Validation result for each registered (external) datastore |
| `ArcGIS Managed Datastore <path>` | Validation result for each managed (internal) datastore |
| `ArcGIS Server License <kind> <name>` | Expiration and validity for each license item (edition, level, extensions, features) |
| `ArcGIS Server Log Settings` | Log level and retention policy |

---

## Check parameters

All check parameter rules are found under **Setup -> Service monitoring rules -> Applications**.

### ArcGIS service state handling (`arcgis_services`)

Controls how service configured/realtime state combinations map to Checkmk states.

| Parameter | Default |
|---|---|
| Configured STARTED, realtime not STARTED | CRIT |
| Configured STOPPED, realtime STOPPED | OK |
| Configured STOPPED, realtime not STOPPED | WARN |
| STARTING or STOPPING (transitional) | WARN |
| FAILED | CRIT |
| Unknown/unexpected states | UNKNOWN |

### ArcGIS Server machine state handling (`arcgis_server_machines`)

Same structure as service state handling, applied to server machines.

| Parameter | Default |
|---|---|
| Configured STARTED, realtime not STARTED | CRIT |
| Configured STOPPED, realtime STOPPED | WARN |
| Configured STOPPED, realtime not STOPPED | WARN |
| STARTING or STOPPING (transitional) | WARN |
| Unknown/unexpected states | UNKNOWN |

### ArcGIS datastore validation handling (`arcgis_datastore_validation`)

Applied to both registered and managed datastore validation checks.

| Parameter | Default |
|---|---|
| Validation successful | OK |
| Validation warning | WARN |
| Validation failure | CRIT |
| Validation error | CRIT |
| Validation unsupported (managed datastores only) | OK |
| Unknown result | UNKNOWN |

### ArcGIS log settings policy (`arcgis_log_settings`)

Applied to both Portal and Server log settings checks.

| Parameter | Default |
|---|---|
| Log level WARNING / WARN / SEVERE | OK (always) |
| Log level INFO | WARN |
| Logging OFF | WARN |
| Log level DEBUG / FINE / VERBOSE | CRIT |
| Log level unknown or empty | UNKNOWN |
| Unexpected log level | WARN |
| Log retention unknown | UNKNOWN |
| Log retention outside expected range | WARN |
| Minimum expected retention | 7 days |
| Maximum expected retention | 365 days |

### ArcGIS Portal license thresholds (`arcgis_portal_license`)

| Parameter | Default |
|---|---|
| License usage warning threshold | 85% |
| License usage critical threshold | 95% |
| Expiration warning | 90 days |
| Expiration critical | 30 days |
| Maximum count unknown | UNKNOWN |
| License expired | CRIT |

### ArcGIS Server license thresholds (`arcgis_server_license`)

| Parameter | Default |
|---|---|
| Expiration warning | 90 days |
| Expiration critical | 30 days |
| License expired | CRIT |
| Feature invalid | CRIT |
| Expiration unknown | UNKNOWN |
| License missing from agent output | UNKNOWN |

### ArcGIS Portal index count handling (`arcgis_portal_indexer`)

| Parameter | Default |
|---|---|
| Database count and index count differ | CRIT |
| Index missing from agent output | UNKNOWN |

### ArcGIS Portal index sync handling (`arcgis_portal_indexer_sync`)

| Parameter | Default |
|---|---|
| Index sync unhealthy | CRIT |
| Index sync status unknown | UNKNOWN |

### ArcGIS federated server handling (`arcgis_portal_federation_servers`)

| Parameter | Default |
|---|---|
| Server reports warnings | WARN |
| Server unhealthy | CRIT |
| Server status unknown | UNKNOWN |
| Server missing from agent output | UNKNOWN |

### ArcGIS Portal federation status handling (`arcgis_portal_federation_status`)

| Parameter | Default |
|---|---|
| Federation reports warnings | WARN |
| Federation unhealthy | CRIT |
| Federation status unknown | UNKNOWN |

### ArcGIS collection status handling (`arcgis_collection_status`)

| Parameter | Default |
|---|---|
| Collection step warning | WARN |
| Collection step skipped | WARN |
| Collection step error | CRIT |
| Collection status unknown | UNKNOWN |

---

## Piggyback host name mapping

The special agent derives piggyback host names from ArcGIS Server names as returned by Portal federation. The server name is used directly as the piggyback target. For Portal machines in a multi-machine deployment, the machine hostname prefix (before the first `.`) is used as the piggyback host name, lowercased.

The target Checkmk host names must match, or Checkmk **host name translation** rules must be used to map piggyback names to existing hosts.

Relevant Checkmk configuration areas:

- **Setup -> Hosts -> Host properties**: piggyback data behavior
- **Setup -> Agents -> Agent access rules -> Host name translations for piggybacked hosts**
- **Setup -> Agents -> Agent access rules -> Processing of piggybacked host data**
- **Setup -> Hosts -> Dynamic host management**: automatic host creation from piggyback data

---

## Troubleshooting

### Show the generated agent command

```bash
cmk -vv --debug -d <portal-host>
```

Look for the `Calling:` line to see the exact command Checkmk generates.

### Run the agent manually

Copy the `Calling:` command and run it as the site user. Add `-v` or `-vv` for more log output:

```bash
/omd/sites/<site>/local/lib/python3/cmk_addons/plugins/arcgis/libexec/agent_arcgis \
  --username '<user>' \
  --password-id '<pw-id>' \
  --portal-url 'https://gis.example.org/portal' \
  -vv \
  <portal-host>
```

### Separate agent output from logs

The agent writes Checkmk sections to stdout and log messages to stderr:

```bash
agent_arcgis ... > /tmp/arcgis_out.txt 2> /tmp/arcgis_err.txt
```

### Other useful commands

```bash
# View raw agent output
cmk -d --debug <portal-host>

# Rediscover services
cmk -II --debug <portal-host>
cmk -II --debug <server-host>

# Run checks
cmk -nv --debug <portal-host>
cmk -nv --debug <server-host>

# List piggyback data
cmk-piggyback list sources
cmk-piggyback list piggybacked
```

### Common issues

**No services on a federated server host** - Verify the Checkmk host name matches the piggyback name the agent emits. Run the agent manually with `-vv` to see what piggyback host names are being used. Check that server collection is enabled and that no include/exclude regex is filtering out the server.

**Portal services present but server services missing** - Check that the ArcGIS account can reach the federated server admin endpoint. Look at the `ArcGIS Collection Status` service for errors, or run the agent manually.

**SSL warnings** - If SSL verification is disabled, the agent logs a warning. For production, enable SSL verification and ensure the Checkmk site trusts the certificate chain used by ArcGIS Enterprise.

**Collection Status is WARN or CRIT** - The `ArcGIS Collection Status` service summarizes errors encountered during collection. Details are shown in the service output. Run the agent with `-vv` to see full error messages.

---

## Security

- Use a dedicated ArcGIS account with the minimum permissions needed for admin endpoint access.
- Store credentials in the Checkmk password store, not in the rule configuration directly.
- Do not share debug output that contains Checkmk password store IDs.
- Enable SSL certificate verification in production environments.

---

## Known limitations

- Tested against ArcGIS Enterprise 11.5 and Checkmk 2.x.
- ArcGIS Enterprise deployments may return different response shapes for license, datastore, or federation endpoints depending on version and configuration. If a service produces unexpected results, run the agent with `-vv` and inspect the raw API responses.
- Federated server filtering affects server collection only. The Portal federation validation check still reflects all servers returned by Portal.
- No performance metrics or graphs are currently included.