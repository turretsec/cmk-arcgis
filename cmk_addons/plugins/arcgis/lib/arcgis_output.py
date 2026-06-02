import time

def output_section(
    section_name: str,
    lines: list[str],
    cache_interval: int | None = None,
) -> None:
    if cache_interval:
        print(f"<<<{section_name}:cached({int(time.time())},{cache_interval})>>>")
    else:
        print(f"<<<{section_name}>>>")
    for line in lines:
        print(line)

def output_piggyback(hostname: str,
    section_name: str,
    lines: list[str],
    cache_interval: int | None = None
) -> None:
    print(f"<<<<{hostname}>>>>")
    output_section(section_name, lines, cache_interval)
    print("<<<<>>>>")

def _safe_text(value: object) -> str:
    return str(value).replace("\n", " ").replace(" ", "_") if value is not None else ""

def portal_license_lines(license_data: dict) -> list[str]:
    lines = []

    lines.append(
        "summary "
        f"{license_data.get('currentRegisteredMembers', 0)} "
        f"{license_data.get('maximumRegisteredMembers', 0)} "
        f"{license_data.get('version', 'unknown')}"
    )

    for user_type in license_data.get("userTypes", []):
        lines.append(
            "userType "
            f"{user_type.get('id', 'unknown')} "
            f"{user_type.get('currentRegisteredMembers', 0)} "
            f"{user_type.get('maximumRegisteredMembers', 0)} "
            f"{user_type.get('expiration', 0)}"
        )

    for app_bundle in license_data.get("appBundles", []):
        lines.append(
            "appBundle "
            f"{app_bundle.get('id', 'unknown')} "
            f"{app_bundle.get('currentRegisteredMembers', 0)} "
            f"{app_bundle.get('maximumRegisteredMembers', 0)} "
            f"{app_bundle.get('expiration', 0)}"
        )

    for app in license_data.get("apps", []):
        lines.append(
            "app "
            f"{app.get('id', 'unknown')} "
            f"{app.get('currentRegisteredMembers', 0)} "
            f"{app.get('maximumRegisteredMembers', 0)} "
            f"{app.get('expiration', 0)}"
        )

    for extension in license_data.get("extensions", []):
        lines.append(
            "extension "
            f"{extension.get('id', 'unknown')} "
            f"{extension.get('currentRegisteredMembers', 0)} "
            f"{extension.get('maximumRegisteredMembers', 0)} "
            f"{extension.get('expiration', 0)}"
        )

    return lines

def server_license_lines(license_data: dict) -> list[str]:
    lines: list[str] = []

    edition = license_data.get("edition")
    if edition:
        lines.append(
            "edition "
            f"{_safe_text(edition.get('name'))} "
            f"{_safe_text(edition.get('version'))} "
            f"{str(edition.get('canExpire', False)).lower()} "
            f"{edition.get('expiration', 0)} "
            f"{_safe_text(edition.get('featureName'))}"
        )

    level = license_data.get("level")
    if level:
        lines.append(
            "level "
            f"{_safe_text(level.get('name'))} "
            f"{_safe_text(level.get('version'))} "
            f"{str(level.get('canExpire', False)).lower()} "
            f"{level.get('expiration', 0)}"
        )

    datafeature = license_data.get("datafeature")
    if datafeature:
        lines.append(
            "datafeature "
            f"{_safe_text(datafeature.get('name'))} "
            f"{_safe_text(datafeature.get('version'))} "
            f"{str(datafeature.get('canExpire', False)).lower()} "
            f"{datafeature.get('expiration', 0)} "
            f"{_safe_text(datafeature.get('ecpCode'))}"
        )

    for extension in license_data.get("extensions", []):
        lines.append(
            "extension "
            f"{_safe_text(extension.get('name'))} "
            f"{_safe_text(extension.get('version'))} "
            f"{str(extension.get('canExpire', False)).lower()} "
            f"{extension.get('expiration', 0)}"
        )

    for feature in license_data.get("features", []):
        lines.append(
            "feature "
            f"{_safe_text(feature.get('name'))} "
            f"{_safe_text(feature.get('displayName'))} "
            f"{feature.get('coreCount', 0)} "
            f"{_safe_text(feature.get('version'))} "
            f"{str(feature.get('canExpire', False)).lower()} "
            f"{feature.get('expiration', 0)} "
            f"{str(feature.get('isValid', True)).lower()}"
        )

    return lines

def portal_indexer_lines(response: dict) -> list[str]:
    lines: list[str] = []
    for index in response.get("indexes", []):
        lines.append(f"{index['name']} {index.get('databaseCount', 0)} {index.get('indexCount', 0)}")
    lines.append(f"syncStatus {response.get('syncStatus', False)}")
    return lines

def portal_validate_federation_lines(response: dict) -> list[str]:
    #print(f"Federation validation response: {response}")
    federation_status = response.get("status", "error")
    #print(f"Parsed federation status: {federation_status}")
    lines = []
    #print(f"Processing serversStatus: {response.get('serversStatus', [])}")
    for server in response.get("serversStatus", []):
        lines.append(f"{server['adminUrl']} {server.get('status', 'error')}")
    lines.append(f"federationStatus {federation_status}")
    #print(f"Parsed federation status lines: {lines}")
    return lines

def log_settings_lines(settings: dict) -> list[str]:
    lines: list[str] = []

    level = (
        settings.get("logLevel")
        or settings.get("log level")
        or settings.get("level")
        or settings.get("loglevel")
        or "UNKNOWN"
    )

    lines.append(f"level {level}")

    max_age = (
        settings.get("maxLogFileAge")
        or settings.get("max log file age")
        or settings.get("maxLogAgeDays")
    )

    if max_age is not None:
        lines.append(f"maxLogFileAge {max_age}")

    log_dir = (
        settings.get("logDir")
        or settings.get("log dir")
        or settings.get("logDirectory")
    )

    if log_dir:
        lines.append(f"logDir {str(log_dir).replace(' ', '_')}")

    return lines