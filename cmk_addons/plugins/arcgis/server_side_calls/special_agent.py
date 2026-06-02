from typing import Iterator
from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

class Params(BaseModel):
    username: str
    password: Secret
    portal_url: str
    verify_ssl: bool = True
    token_expiry: int = 60

def _generate_arcgis_command(
    params: Params,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--username",
        params.username,
        "--password-id",
        params.password,
        "--portal-url",
        params.portal_url,
        "--token-expiry",
        str(params.token_expiry),
    ]

    if not params.verify_ssl:
        args.append("--no-verify-ssl")

    args.append(host_config.name)

    yield SpecialAgentCommand(command_arguments=args)

special_agent_arcgis = SpecialAgentConfig(
    name="arcgis",
    parameter_parser=Params.model_validate,
    commands_function=_generate_arcgis_command,
)