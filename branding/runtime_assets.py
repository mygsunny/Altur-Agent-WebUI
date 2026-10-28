"""Source-bound display leaf edits for reviewed bundled YAML manifests."""
from __future__ import annotations

import copy
import json


def _yaml():
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError('Install the documented branding dependencies before generating runtime manifest copy.') from exc
    return yaml


def yaml_spans(source: str, record: dict) -> dict[str, list[tuple[int, int]]]:
    yaml = _yaml()
    root = yaml.compose(source)
    result = {}
    for slot in record['slots']:
        node = root
        for key in slot['key_path']:
            if isinstance(node, yaml.MappingNode):
                matches = [value for name, value in node.value if name.value == str(key)]
                if len(matches) != 1:
                    raise RuntimeError('Runtime manifest display path is missing or ambiguous.')
                node = matches[0]
            elif isinstance(node, yaml.SequenceNode) and isinstance(key, int):
                node = node.value[key]
            else:
                raise RuntimeError('Runtime manifest display path is invalid.')
        if not isinstance(node, yaml.ScalarNode) or node.tag != 'tag:yaml.org,2002:str':
            raise RuntimeError('Only manifest display string leaves may be branded.')
        expression = source[node.start_mark.index:node.end_mark.index]
        if expression != slot['upstream_literal']:
            raise RuntimeError('Runtime manifest display value differs from the reviewed source.')
        result.setdefault(expression, []).append((node.start_mark.index, node.end_mark.index))
    return result


def _masked(data, slots):
    result = copy.deepcopy(data)
    for slot in slots:
        target = result
        path = slot['key_path']
        for key in path[:-1]:
            target = target[key]
        if not isinstance(target[path[-1]], str):
            raise RuntimeError('Runtime manifest patch changes a value type.')
        target[path[-1]] = '<approved display leaf>'
    return result


def validate_yaml_patch(original: str, replacement: str, record: dict) -> None:
    yaml = _yaml()
    try:
        before, after = yaml.safe_load(original), yaml.safe_load(replacement)
        if _masked(before, record['slots']) != _masked(after, record['slots']):
            raise RuntimeError('Runtime manifest patch changes an unapproved value.')
        # JSON files use the same node coordinates but must remain strict JSON.
        if record.get('format') == 'json':
            json.loads(replacement)
    except (yaml.YAMLError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError('Runtime manifest patch is not valid structured data.') from exc
