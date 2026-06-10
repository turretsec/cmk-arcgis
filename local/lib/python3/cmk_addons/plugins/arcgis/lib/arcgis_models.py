from pydantic import BaseModel, Field
from typing import Any, Literal

class PortalMachine(BaseModel):
    machine_name: str = Field(alias="machineName")
    role: str | None = None

class PortalMachineHealth(BaseModel):
    machine_name: str = Field(alias="machineName")
    status: str | None = None
    role: Literal["primary", "secondary", "standalone"] = "standalone"

class PortalIndex(BaseModel):
    name: str
    database_count: int = Field(default=0, alias="databaseCount")
    index_count: int = Field(default=0, alias="indexCount")

class PortalIndexerStatus(BaseModel):
    indexes: list[PortalIndex] = Field(default_factory=list)
    sync_status: bool = Field(default=False, alias="syncStatus")

class ArcGISServiceStatus(BaseModel):
    name: str
    configured_state: str = "UNKNOWN"
    realtime_state: str = "UNKNOWN"

class DataItemValidationDetail(BaseModel):
    data_item: str = Field(default="", alias="dataItem")
    path: str | None = None
    validation_state: str | None = Field(default=None, alias="validationState")
    message: str | None = None


class DataItemValidationMachine(BaseModel):
    machine: str
    status: str | None = None
    data_items: list[DataItemValidationDetail] = Field(
        default_factory=list,
        alias="dataItems",
    )

class RegisteredDataStoreValidationResponse(BaseModel):
    success: bool | str | None = None
    status: str | None = None
    machines: list[DataItemValidationMachine] = Field(default_factory=list)

    raw: dict[str, Any] = Field(default_factory=dict)

class RegisteredDataStoreHealth(BaseModel):
    path: str
    store_type: str
    status: str
    message: str = ""
    machine: str | None = None