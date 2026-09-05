"""Regression for the private build's missing-property-description failure."""
import copy
import json
from pathlib import Path
import unittest
from scripts.check_apify_schema import validate_schema

ROOT=Path(__file__).resolve().parents[1]

class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema=json.loads((ROOT/'.actor/input_schema.json').read_text())

    def test_all_properties_have_metadata(self):
        validate_schema(self.schema)

    def test_reported_build_failure_is_caught_locally(self):
        del self.schema['properties']['use_case']['description']
        with self.assertRaisesRegex(ValueError, r'schema.properties.use_case.description is required'):
            validate_schema(self.schema)

    def test_each_top_level_and_nested_field_metadata_required(self):
        fields=[(name,None) for name in self.schema['properties']]
        fields += [('installed_runtime_versions',name) for name in ('ollama','mlx')]
        for name,child in fields:
            for key in ('title','description','editor'):
                with self.subTest(name=name,child=child,key=key):
                    schema=copy.deepcopy(self.schema)
                    node=schema['properties'][name]
                    if child:node=node['properties'][child]
                    del node[key]
                    with self.assertRaises(ValueError):validate_schema(schema)

    def test_frozen_fields_and_choices_unchanged(self):
        props=self.schema['properties']
        self.assertEqual(set(props),{'device_chip','memory_gib','use_case','operating_system','preferred_runtime','minimum_context_tokens','latency_preference','installed_runtime_versions','constraints'})
        self.assertEqual(self.schema['required'],['device_chip','memory_gib','use_case','operating_system'])
        self.assertEqual(props['use_case']['enum'],['chat','coding','reasoning'])
        self.assertEqual(props['latency_preference']['enum'],['quality','balanced','speed'])
        self.assertEqual(props['preferred_runtime']['enum'],['ollama','mlx','no preference'])
