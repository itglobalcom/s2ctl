from typing import List, TypedDict

from ssclient.base import BaseService


class SshkeyEntity(TypedDict):
    id: int  # noqa: WPS125
    name: str
    public_key: str


class SshkeyService(BaseService):
    path = 'api/v1/ssh-keys'

    async def create(self, *, name: str, public_key: str) -> SshkeyEntity:
        return await self._http_client.post(
            path=self.path,
            payload={
                'name': name,
                'public_key': public_key,
            },
        )

    async def get(self, sshkey_id: int) -> SshkeyEntity:
        path = self._make_path(str(sshkey_id))
        ssh_resp = await self._http_client.get(path)
        return ssh_resp['ssh_key']

    async def list(self) -> List[SshkeyEntity]:  # noqa: WPS125
        sshs_resp = await self._http_client.get(self.path)
        return sshs_resp['ssh_keys']

    async def delete(self, sshkey_id: int) -> None:
        path = self._make_path(str(sshkey_id))
        await self._http_client.delete(path)
