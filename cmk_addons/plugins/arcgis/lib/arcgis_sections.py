from pydantic import BaseModel, Field

# Collection status section

class CollectionStatusEntry(BaseModel):
    component: str
    target: str
    status: str
    message: str = ""

class SectionCollectionStatus(BaseModel):
    entries: list[CollectionStatusEntry] = Field(default_factory=list)

# Portal license section

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
    summary: PortalLicenseSummary
    items: list[PortalLicenseEntry] = Field(default_factory=list)

# Registered datastore section

class RegisteredDatastoreValidation(BaseModel):
    path: str
    store_type: str
    status: str
    message: str = ""
    machine: str | None = None

class SectionRegisteredDatastoreValidation(BaseModel):
    validations: list[RegisteredDatastoreValidation] = Field(default_factory=list)

# Managed datastore section

class ManagedDatastoreValidation(BaseModel):
    path: str
    classification: str
    message: str = ""

class SectionManagedDatastoreValidation(BaseModel):
    validations: list[ManagedDatastoreValidation] = Field(default_factory=list)

# Server license section

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

# Portal health section

class SectionPortalHealth(BaseModel):
    status: str
    role: str = "standalone"

# Portal indexer section

class PortalIndexCount(BaseModel):
    name: str
    database_count: int
    index_count: int

class SectionPortalIndexer(BaseModel):
    indexes: list[PortalIndexCount] = Field(default_factory=list)
    sync_status: bool | None = None

# Portal federation section

class PortalFederatedServerStatus(BaseModel):
    admin_url: str
    status: str

class SectionPortalFederation(BaseModel):
    servers: list[PortalFederatedServerStatus] = Field(default_factory=list)
    federation_status: str = "unknown"

# Server services section

class ArcGISServiceState(BaseModel):
    name: str
    configured_state: str
    realtime_state: str

class SectionArcGISServices(BaseModel):
    services: list[ArcGISServiceState] = Field(default_factory=list)

# Server machines section

class ArcGISServerMachineState(BaseModel):
    name: str
    configured_state: str
    realtime_state: str

class SectionArcGISServerMachines(BaseModel):
    machines: list[ArcGISServerMachineState] = Field(default_factory=list)

# Server log settings section

class SectionArcGISLogSettings(BaseModel):
    level: str = "UNKNOWN"
    max_log_file_age: int | None = None
    log_dir: str | None = None