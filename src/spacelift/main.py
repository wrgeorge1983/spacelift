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

    def get_stack_by_id(self, stack_id: str, query_fields: Optional[list[str]] = None) -> dict:
        if query_fields is None:
            query_fields = ["id", "space"]
        query_text = f'query Stack($id: ID!) {{ stack(id: $id) {{ {" ".join(query_fields)}  }} }}'
        variable_values = {
            "id": stack_id,
        }
        query = gql(query_text)
        return self._execute(query, variable_values=variable_values)["stack"]

    def get_spaces(self, query_fields: Optional[list[str]] = None) -> list[dict]:
        if query_fields is None:
            query_fields = ["id", "name"]
        query_text = f'query Spaces {{ spaces {{ {" ".join(query_fields)}  }} }}'
        query = gql(query_text)
        return self._execute(query)["spaces"]

    def get_space_by_id(self, space_id: str, query_fields: Optional[list[str]] = None) -> dict:
        if query_fields is None:
            query_fields = ["id", "name"]
        query_text = f'query Space($id: ID!) {{ space(id: $id) {{ {" ".join(query_fields)}  }} }}'
        variable_values = {
            "id": space_id,
        }
        query = gql(query_text)
        return self._execute(query, variable_values=variable_values)["space"]

    def get_contexts(self, query_fields: Optional[list[str]] = None) -> list[dict]:
        if query_fields is None:
            query_fields = ["id", "name"]
        query_text = f'query Contexts {{ contexts {{ {" ".join(query_fields)}  }} }}'
        query = gql(query_text)
        return self._execute(query)["contexts"]

    def get_context_by_id(self, context_id: str, query_fields: Optional[list[str]] = None) -> dict:
        if query_fields is None:
            query_fields = ["id", "name", ]
        query_text = f'query Context($id: ID!) {{ context(id: $id) {{ {" ".join(query_fields)}  }} }}'
        variable_values = {
            "id": context_id,
        }
        query = gql(query_text)
        return self._execute(query, variable_values=variable_values)["context"]

    def create_context(self, context_name: str, space_id: str, description: str = '', labels: list[str] = None, envvars: list[dict] = None):
        if labels is None:
            labels = []
        if envvars is None:
            envvars = []

        query_text = f"""
        mutation ContextCreateV2($name: String!, $envvars: [ConfigInput!], $space: ID, $description: String, $labels: [String!]) {{
            contextCreateV2(input: {{name: $name, configAttachments: $envvars, space: $space, description: $description, labels: $labels }}) {{
                id
                name
                config {{
                    id
                    value
                }}
            }}
        }}
        """

        variable_values = {
            "name": context_name,
            "description": description,
            "labels": labels,
            "space": space_id,
            "envvars": envvars,
        }

        query = gql(query_text)
        result = self._execute(query, variable_values=variable_values)
        log.debug(f"create_context result: {result}")
        return result

    def delete_context(self, context_id: str):
        query_text = f"""
        mutation ContextDelete($id: ID!) {{
            contextDelete(id: $id) {{
                id
            }}
        }}
        """
        variable_values = {
            "id": context_id,
        }
        query = gql(query_text)
        result = self._execute(query, variable_values=variable_values)
        log.debug(f"delete_context result: {result}")
        return result

    def create_space(self, space_name: str, parent_space_id: str, description: str, labels: list[str] = None, inherit_entities: bool = True):
        if labels is None:
            labels = []

        query_text = f"""
        mutation SpaceCreate($name: String!, $parent: ID!, $description: String!, $labels: [String!], $inheritEntities: Boolean!) {{
            spaceCreate(input: {{name: $name, parentSpace: $parent, description: $description, labels: $labels, inheritEntities: $inheritEntities}}) {{
                id
                name
                description
                labels
            }}
        }}
        """
        variable_values = {
            "name": space_name,
            "parent": parent_space_id,
            "description": description,
            "labels": labels,
            "inheritEntities": inherit_entities,
        }
        query = gql(query_text)
        result = self._execute(query, variable_values=variable_values)
        log.debug(f"create_space result: {result}")
        return result

    def delete_space(self, space_id: str):
        query_text = f"""
        mutation SpaceDelete($id: ID!) {{
            spaceDelete(space: $id) {{
                id
            }}
        }}
        """
        variable_values = {
            "id": space_id,
        }
        query = gql(query_text)
        result = self._execute(query, variable_values=variable_values)
        log.debug(f"delete_space result: {result}")
        return result



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
    # result = sl.get_stacks()
    # print(result)
    #
    # result = sl.get_stacks(["id", "name", "branch", "namespace", "repository", "state"])
    # print(result)

    # result = sl.get_context_by_id(context_id="customer-a", query_fields=["id", "name", "config { id value writeOnly }"])
    LIBRARY_TEST_NAME = "library-test-customer-a"

    try:
        result = sl.create_context(context_name=LIBRARY_TEST_NAME, space_id="root", envvars=[
            {"id": "FOO", "value": "bar", "type": "ENVIRONMENT_VARIABLE", "writeOnly": False},
            {"id": "BAZ", "value": "qux", "type": "ENVIRONMENT_VARIABLE", "writeOnly": True}])
        print(f'create_context result: {result}')

    except Exception as e:
        result = sl.delete_context(context_id=LIBRARY_TEST_NAME)
        print(f'delete_context result: {result}')

    spaces = sl.get_spaces()

    delete_spaces = [space for space in spaces if space["name"] == LIBRARY_TEST_NAME]
    print(result)

    for space in delete_spaces:
        print(space["id"])
        result = sl.delete_space(space_id=space["id"])
        print(f'delete_space result: {result}')

    if not spaces:
        result = sl.create_space(space_name=LIBRARY_TEST_NAME, parent_space_id="root", description=f"{LIBRARY_TEST_NAME} space", labels=["customer", "a"])

        print(f'create_space result: {result}')


if __name__ == "__main__":
    main()
