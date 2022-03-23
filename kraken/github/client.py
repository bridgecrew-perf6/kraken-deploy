import json
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import parse_obj_as

from .types import Commit, Deployment


class Client(Protocol):
    def get_latest_deployment(self, *, environment: str) -> Deployment | None:
        ...

    def get_commits(self, *, branch: str, page: int = ...) -> list[Commit]:
        ...

    def create_deployment(self, *, environment: str, commit: str) -> None:
        ...


class GithubClient(Client):
    def __init__(self, *, repo: str, base_url: str) -> None:
        self.repo = repo
        self.base_url = base_url

    def get_latest_deployment(self, *, environment: str) -> Deployment | None:
        """
        Get the latest deployment, including statuses, in the given environment
        """

        deployments = self._request(
            "GET",
            f"/repos/{self.repo}/deployments",
            params={"environment": environment, "per_page": "1"},
        )

        assert isinstance(deployments, list)

        deployment = deployments[0]
        if isinstance(deployment, dict):
            deployment["statuses"] = self._request(
                "GET",
                f"/repos/{self.repo}/deployments/{deployment['id']}/statuses",
            )

        return Deployment.parse_obj(deployment)

    def get_commits(self, *, branch: str, page: int = 1) -> list[Commit]:

        data = self._request(
            "GET", f"/repos/{self.repo}/commits", params={"page": str(page)}
        )

        return parse_obj_as(list[Commit], data)

    def _request(
        self, method: str, path: str, *, params: dict[str, str] | None = None
    ) -> Any:
        """
        Perform an HTTP request against the github API and return the decoded json.
        """

        assert path.startswith("/")
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"

        request = Request(method=method, url=url)

        with urlopen(request) as response:
            # urlopen should raise an exception if the status is non-200
            assert 100 < response.status < 300

            data = response.read().decode("utf-8")

            return json.loads(data)
