#!/usr/bin/env python3
"""Offline structural guard for known Apify schema requirements, not provider validation."""
import json
from pathlib import Path


def validate_schema(schema):
    if schema.get('schemaVersion') != 1 or schema.get('type') != 'object':
        raise ValueError('Root must be an object with schemaVersion 1')
    def check(node, path, is_field=False):
        for key in ('title', 'description'):
            if not isinstance(node.get(key), str) or not node[key].strip():
                raise ValueError(f'{path}.{key} is required')
        if is_field:
            allowed = {'string': {'textfield','textarea','select'}, 'integer': {'number'}, 'object': {'json'}}
            if node.get('editor') not in allowed.get(node.get('type'), set()):
                raise ValueError(f'{path}.editor is missing or unsupported by this local guard')
        properties = node.get('properties', {})
        if not isinstance(properties, dict):
            raise ValueError(f'{path}.properties must be an object')
        required = node.get('required', [])
        if not isinstance(required, list) or not set(required) <= properties.keys():
            raise ValueError(f'{path}.required names an undefined field')
        if 'enum' in node and (not isinstance(node['enum'], list) or not node['enum'] or len(set(node['enum'])) != len(node['enum'])):
            raise ValueError(f'{path}.enum must contain distinct choices')
        for name, child in properties.items():
            check(child, f'{path}.properties.{name}', True)
    check(schema, 'schema')


if __name__ == '__main__':
    path=Path(__file__).resolve().parents[1]/'.actor/input_schema.json'
    validate_schema(json.loads(path.read_text()))
    print('PASS: recursive field metadata and local structural checks; provider validation pending')
