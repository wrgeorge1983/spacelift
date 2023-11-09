import random
import string
from typing import Optional

from spacelift import Spacelift


def field_filter(item: dict, query_fields: list[str]):
    return {field: item[field] for field in item if field in query_fields}


class MockSpacelift:
    def __init__(self):
        self.base_url = "http://test_spacelift"
        self.key_id = "abc"
        self.key_secret = "xyz"
        self._data = {"spaces": [], "stacks": [], "contexts": []}
        self._jwt = "mock_jwt"

    @property
    def jwt(self):
        return self._jwt

    def get_stacks(self, query_fields: Optional[list[str]] = None) -> list[dict]:
        if query_fields is None:
            query_fields = ["id", "space"]

        stacks = self._data["stacks"]
        stacks = [field_filter(stack, query_fields) for stack in stacks]
        return stacks

    def get_stack_by_id(self, stack_id: str, query_fields: Optional[list[str]] = None):
        if query_fields is None:
            query_fields = ["id", "space"]

        stacks = self.get_stacks(query_fields=query_fields)
        stacks = [stack for stack in stacks if stack["id"] == stack_id]
        if len(stacks) == 0:
            return None

        return stacks[0]

    def get_spaces(self, query_fields: Optional[list[str]] = None) -> list[dict]:
        if query_fields is None:
            query_fields = ["id", "name"]

        spaces = self._data["spaces"]
        spaces = [field_filter(space, query_fields) for space in spaces]
        return spaces

    def get_space_by_id(self, space_id: str, query_fields: Optional[list[str]] = None):
        if query_fields is None:
            query_fields = ["id", "name"]

        spaces = self.get_spaces(query_fields=query_fields)
        spaces = [space for space in spaces if space["id"] == space_id]
        if len(spaces) == 0:
            return None

        return spaces[0]

    def get_contexts(self, query_fields: Optional[list[str]] = None):
        if query_fields is None:
            query_fields = ["id", "name"]

        config_fields = []
        for field in query_fields:
            if field.startswith("config"):
                query_fields.remove(field)
                query_fields.append("config")
                config_fields = field.split(" ")[1:]
                config_fields = [
                    config_field
                    for config_field in config_fields
                    if config_field not in "{}"
                ]

        contexts = self._data["contexts"]
        contexts = [field_filter(context, query_fields) for context in contexts]

        if "config" in query_fields:
            for context in contexts:
                context["config"] = [
                    field_filter(envvar, config_fields) for envvar in context["config"]
                ]

        return contexts

    def get_context_by_id(
        self, context_id: str, query_fields: Optional[list[str]] = None
    ):
        if query_fields is None:
            query_fields = ["id", "name"]

        contexts = self.get_contexts(query_fields=query_fields)
        contexts = [context for context in contexts if context["id"] == context_id]
        if len(contexts) == 0:
            return None

        return contexts[0]

    def create_context(
        self,
        context_name: str,
        space_id: str,
        description: str = "",
        labels: list[str] = None,
        envvars: list[dict] = None,
    ):
        if labels is None:
            labels = []
        if envvars is None:
            envvars = []

        parent_space = self.get_space_by_id(space_id)
        if parent_space is None:
            raise Exception({"message": "unauthorized", "path": ["contextCreateV2"]})

        config = [
            {
                "id": envvar["id"],
                "value": envvar["value"],
                "writeOnly": False,
            }
            for envvar in envvars
        ]

        item = {
            "name": context_name,
            "id": context_name,
            "space": space_id,
            "description": description,
            "labels": labels,
            "config": config,
        }

        contexts = self._data["contexts"]
        for context in contexts:
            if context["name"] == context_name:
                raise Exception(
                    {
                        "message": "could not persist context: context with this slug already exists for this account",
                        "path": ["contextCreateV2"],
                    }
                )

        contexts.append(item)

        return {"contextCreateV2": field_filter(item, query_fields=["id", "name"])}

    def delete_context(self, context_id: str):
        contexts = self._data["contexts"]
        for context in contexts:
            if context["id"] == context_id:
                contexts.remove(context)
                return {"contextDelete": {"id": context_id}}

        return {"contextDelete": None}

    def create_space(
        self,
        space_name: str,
        parent_space_id: str,
        description: str = "",
        labels: list[str] = None,
        inherit_entities: bool = True,
    ):
        if labels is None:
            labels = []

        if space_name not in ("root", "legacy"):
            generated_id = "".join(
                random.choice(string.ascii_lowercase + string.digits) for _ in range(16)
            )
            id = f"{space_name}-{generated_id}"
        else:
            id = space_name

        parent_space = self.get_space_by_id(parent_space_id)
        if parent_space is None:
            if space_name == parent_space_id == "root":
                parent_space_id = None
                pass  # this is fine to create the root space
            else:
                raise Exception(
                    {"message": "parent space not found", "path": ["spaceCreate"]}
                )

        item = {
            "name": space_name,
            "id": id,
            "parent": parent_space_id,
            "description": description,
            "labels": labels,
            "inherit_entities": inherit_entities,
        }

        spaces = self._data["spaces"]
        spaces.append(item)

        return {"spaceCreate": field_filter(item, query_fields=["id", "name"])}

    def delete_space(self, space_id: str):
        spaces = self._data["spaces"]
        for space in spaces:
            if space["id"] == space_id:
                spaces.remove(space)
                return {"spaceDelete": {"id": space_id}}

        return {"spaceDelete": None}

    def trigger_run(self, stack_id: str, query_fields: Optional[list[str]] = None):
        raise NotImplementedError()
