from pydantic import BaseModel, Field


class CollectionStatusEntry(BaseModel):
    component: str
    target: str
    status: str
    message: str = ""


class SectionCollectionStatus(BaseModel):
    entries: list[CollectionStatusEntry] = Field(default_factory=list)


class PortalLicenseEntry(BaseModel):
    kind: str
    id: str
    current: int = 0
    maximum: int = 0
    expiration: int = 0


class PortalLicenseSummary(BaseModel):
    current: int = 0
    maximum: int = 0
    version: str = "unknown"


class SectionPortalLicense(BaseModel):
    summary: PortalLicenseSummary = Field(default_factory=PortalLicenseSummary)
    items: list[PortalLicenseEntry] = Field(default_factory=list)


class RegisteredDatastoreValidation(BaseModel):
    path: str
    store_type: str
    status: str
    message: str = ""
    machine: str | None = None


class SectionRegisteredDatastoreValidation(BaseModel):
    validations: list[RegisteredDatastoreValidation] = Field(default_factory=list)


class ManagedDatastoreValidation(BaseModel):
    path: str
    classification: str
    message: str = ""


class SectionManagedDatastoreValidation(BaseModel):
    validations: list[ManagedDatastoreValidation] = Field(default_factory=list)


class ServerLicenseEntry(BaseModel):
    kind: str
    name: str
    version: str = "unknown"
    can_expire: bool = False
    expiration: int = 0
    display_name: str | None = None
    core_count: int = 0
    is_valid: bool = True
    extra: str = ""


class SectionServerLicense(BaseModel):
    entries: list[ServerLicenseEntry] = Field(default_factory=list)


class SectionPortalHealth(BaseModel):
    status: str
    role: str = "standalone"


class PortalIndexCount(BaseModel):
    name: str
    database_count: int
    index_count: int


class SectionPortalIndexer(BaseModel):
    indexes: list[PortalIndexCount] = Field(default_factory=list)
    sync_status: bool | None = None


class PortalFederatedServerStatus(BaseModel):
    admin_url: str
    status: str


class SectionPortalFederation(BaseModel):
    servers: list[PortalFederatedServerStatus] = Field(default_factory=list)
    federation_status: str = "unknown"


class ArcGISServiceState(BaseModel):
    name: str
    configured_state: str
    realtime_state: str


class SectionArcGISServices(BaseModel):
    services: list[ArcGISServiceState] = Field(default_factory=list)


class ArcGISServerMachineState(BaseModel):
    name: str
    configured_state: str
    realtime_state: str


class SectionArcGISServerMachines(BaseModel):
    machines: list[ArcGISServerMachineState] = Field(default_factory=list)


class SectionArcGISLogSettings(BaseModel):
    level: str = "UNKNOWN"
    max_log_file_age: int | None = None
    log_dir: str | None = None

class ServiceStatsEntry(BaseModel):
    service_name: str
    window_seconds: int
    request_count: int = 0
    failed_requests: int = 0
    timed_out_requests: int = 0
    avg_response_time_ms: float | None = None
    max_response_time_ms: float | None = None
    avg_wait_time_ms: float | None = None
    max_wait_time_ms: float | None = None
    max_running_instances: int | None = None
 
 
class SectionArcGISServiceStats(BaseModel):
    services: list[ServiceStatsEntry] = Field(default_factory=list)
 
 
class SectionArcGISServerMode(BaseModel):
    site_mode: str = "UNKNOWN"
 
 
class WebAdaptorEntry(BaseModel):
    web_adaptor_url: str
    machine_name: str
    http_port: int = 80
    https_port: int = 443
    is_admin_enabled: bool = False
    description: str = ""
 
 
class SectionArcGISWebAdaptors(BaseModel):
    web_adaptors: list[WebAdaptorEntry] = Field(default_factory=list)
