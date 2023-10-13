import os
from typing import Optional

from gql import gql, Client
from graphql import DocumentNode
from gql.transport.requests import RequestsHTTPTransport


class Spacelift:
    def __init__(self, base_url: Optional[str] = None, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        params = self._validate_params(base_url, key_id, key_secret)
        self.base_url = params['base_url']
        self.key_id = params['key_id']
        self.key_secret = params['key_secret']
        self._jwt = None
        self.headers = {}
        self.transport = RequestsHTTPTransport(url=self.base_url, headers=self.headers)
        self.client = Client(transport=self.transport)

    @staticmethod
    def _validate_params(base_url: Optional[str] = None, key_id: Optional[str] = None,
                         key_secret: Optional[str] = None) -> dict:
        """Ensures each parameter is provided by either the constructor or environment variables."""
        base_url = base_url or os.environ.get('SPACELIFT_BASE_URL')
        key_id = key_id or os.environ.get('SPACELIFT_KEY_ID')
        key_secret = key_secret or os.environ.get('SPACELIFT_KEY_SECRET')
        result = {
            'base_url': base_url,
            'key_id': key_id,
            'key_secret': key_secret,
        }
        null_params = [k for k, v in result.items() if not v]
        if null_params:
            raise ValueError(f'Invalid spacelift params: {null_params}')
        return result

    def _execute(self, query: DocumentNode, variable_values: Optional[dict] = None) -> dict:
        self.transport.headers['Authorization'] = f'Bearer {self.jwt}'
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
            'keyId': self.key_id,
            'keySecret': self.key_secret,
        }
        query = gql(query_text)
        result = self.client.execute(query,
                                     variable_values=variable_values)  # cannot use self._execute() here because it would cause infinite recursion
        print(result)
        if result.get('apiKeyUser') is None:
            raise ValueError(f'Invalid spacelift keyId: {self.key_id}')
        return result['apiKeyUser']['jwt']

    @property
    def jwt(self):
        if not self._jwt:
            self._jwt = self._get_jwt()
        return self._jwt

    def get_stacks(self, fields: Optional[list[str]] = None) -> list[dict]:
        if fields is None:
            fields = ['id', 'space', 'administrative', 'apiHost']
        query_text = f'query Stacks {{ stacks {{ {" ".join(fields)}  }} }}'
        query = gql(query_text)
        return self._execute(query)['stacks']


def main():
    sl = Spacelift("https://apcela.app.spacelift.io/graphql", key_id, key_secret)
    result = sl.get_stacks()
    print(result)


if __name__ == "__main__":
    main()
