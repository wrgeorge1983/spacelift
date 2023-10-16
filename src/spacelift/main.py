import os
from typing import Optional

from gql import gql, Client
from graphql import DocumentNode
from gql.transport.requests import RequestsHTTPTransport

from logging import getLogger

log = getLogger(__name__)


class Spacelift:
    def __init__(
        self,
        base_url: Optional[str] = None,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ):
        params = self._validate_params(base_url, key_id, key_secret)
        self.base_url = params["base_url"]
        self.key_id = params["key_id"]
        self.key_secret = params["key_secret"]
        self._jwt = None
        self.headers = {}
        self.transport = RequestsHTTPTransport(url=self.base_url, headers=self.headers)
        self.client = Client(transport=self.transport)

    @staticmethod
    def _validate_params(
        base_url: Optional[str] = None,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ) -> dict:
        """
        Ensures each parameter is provided by either the constructor or environment variables.
        TODO: add support for spacelift's CLI config file, etc.
        """
        base_url = base_url or os.environ.get("SPACELIFT_BASE_URL")
        key_id = key_id or os.environ.get("SPACELIFT_KEY_ID")
        key_secret = key_secret or os.environ.get("SPACELIFT_KEY_SECRET")
        result = {
            "base_url": base_url,
            "key_id": key_id,
            "key_secret": key_secret,
        }
        null_params = [k for k, v in result.items() if not v]
        if null_params:
            raise ValueError(f"Missing spacelift params: {null_params}")
        return result

    def _execute(
        self, query: DocumentNode, variable_values: Optional[dict] = None
    ) -> dict:
        self.transport.headers["Authorization"] = f"Bearer {self.jwt}"
        return self.client.execute(query, variable_values=variable_values)

    def _get_jwt(self):
        query_text = f"""
        mutation GetSpaceliftToken($keyId: ID!, $keySecret: String!) {{
            apiKeyUser(id: $keyId, secret: $keySecret) {{
                id
                jwt
            }}
        }}
        """
        variable_values = {
            "keyId": self.key_id,
            "keySecret": self.key_secret,
        }
        query = gql(query_text)
        result = self.client.execute(
            query, variable_values=variable_values
        )  # cannot use self._execute() here because it would cause infinite recursion
        log.debug(f"get_jwt result: {result}")
        if result.get("apiKeyUser") is None:
            raise ValueError(f"Invalid spacelift keyId: {self.key_id}")
        return result["apiKeyUser"]["jwt"]

    @property
    def jwt(self):
        if not self._jwt:
            self._jwt = self._get_jwt()
        return self._jwt

    def get_stacks(self, query_fields: Optional[list[str]] = None) -> list[dict]:
        if query_fields is None:
            query_fields = ["id", "space"]
        query_text = f'query Stacks {{ stacks {{ {" ".join(query_fields)}  }} }}'
        query = gql(query_text)
        return self._execute(query)["stacks"]

    def trigger_run(self, stack_id: str, query_fields: Optional[list[str]] = None):
        if query_fields is None:
            query_fields = ["id", "branch"]

        query_text = f"""
        mutation RunTrigger($stack: ID!) {{
            runTrigger(stack: $stack, runType: PROPOSED) {{
                {" ".join(query_fields)}
            }}
        }}
        """
        variable_values = {
            "stack": stack_id,
        }
        query = gql(query_text)
        result = self._execute(query, variable_values=variable_values)["runTrigger"]
        log.debug(f"trigger_run result: {result}")
        return result


def main():
    sl = Spacelift(os.environ.get("SPACELIFT_BASE_URL"))
    result = sl.get_stacks()
    print(result)

    result = sl.get_stacks(["id", "name", "branch", "namespace", "repository", "state"])
    print(result)


if __name__ == "__main__":
    main()
