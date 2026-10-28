"""Validate this design package. Requires jsonschema; does not test a platform."""
from pathlib import Path
import json
import re
import sys
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
errors = []
checks = []

def check(condition, message):
    if not condition:
        errors.append(message)

schema = json.loads((ROOT / 'contracts/domain.schema.json').read_text())
Draft202012Validator.check_schema(schema)
checks.append('Domain JSON Schema is valid Draft 2020-12.')
api = json.loads((ROOT / 'contracts/openapi.json').read_text())
check(api['openapi'] == '3.1.0', 'Unexpected OpenAPI version')

def local_refs(value, document, location):
    if isinstance(value, dict):
        if '$ref' in value and value['$ref'].startswith('#/'):
            target = document
            try:
                for item in value['$ref'][2:].split('/'):
                    target = target[item.replace('~1', '/').replace('~0', '~')]
            except (KeyError, TypeError):
                errors.append(f'Broken schema reference at {location}: {value["$ref"]}')
        for k, v in value.items():
            local_refs(v, document, f'{location}/{k}')
    elif isinstance(value, list):
        for i, v in enumerate(value):
            local_refs(v, document, f'{location}/{i}')

local_refs(schema, schema, 'domain')
local_refs(api, api, 'openapi')
checks.append('All local domain/OpenAPI schema references resolve.')
ids = []
for path, methods in api['paths'].items():
    for method, op in methods.items():
        ids.append(op['operationId'])
        declared = {p['name'] for p in op.get('parameters', []) if p['in'] == 'path' and p.get('required')}
        check(declared == set(re.findall(r'{(\w+)}', path)), f'Path parameter mismatch: {path}')
        check(any(k.startswith('2') for k in op['responses']), f'No success response: {path}')
check(len(ids) == len(set(ids)), 'Duplicate API operation IDs')
checks.append(f'{len(ids)} API operations have unique IDs and matching required path parameters.')
for name, definition in api['components']['schemas'].items():
    Draft202012Validator.check_schema(definition)
checks.append('OpenAPI component schemas are structurally valid JSON Schemas.')
examples = {'job-request.json':'JobRequest','requirement-spec.json':'RequirementSpec','assertion-oracle.json':'AssertionOracle','validation-report.json':'ValidationReport'}
for filename, name in examples.items():
    value = json.loads((ROOT / 'examples' / filename).read_text())
    validator = Draft202012Validator({'$schema':schema['$schema'], '$defs':schema['$defs'], '$ref':f'#/$defs/{name}'}, format_checker=FormatChecker())
    for error in validator.iter_errors(value):
        errors.append(f'{filename}: {list(error.path)}: {error.message}')
checks.append('Four synthetic examples conform to their named domain contracts.')
lld = (ROOT/'03-LLD.md').read_text()
requirements = (ROOT/'01-REQUIREMENTS.md').read_text()
for enum_name in ['JobState', 'Stage', 'QualityOutcome']:
    for value in schema['$defs'][enum_name]['enum']:
        check(value in lld, f'{enum_name} missing from LLD: {value}')
        check(value in requirements, f'{enum_name} missing from requirements: {value}')
checks.append('Lifecycle, stage and quality enum values are present in both requirements and LLD.')
request = json.loads((ROOT/'examples/job-request.json').read_text())
check(sum(r['role']=='automation' for r in request['repository_refs']) == 1, 'Example must have exactly one automation target')
report = json.loads((ROOT/'examples/validation-report.json').read_text())
check(report['quality_outcome']=='SUSPECTED_PRODUCT_DEFECT' and not report['merge_eligible'] and report['result_summary']['failed']==1, 'Defect example hides a failing test')
req = (ROOT/'01-REQUIREMENTS.md').read_text()
eval_text = (ROOT/'06-ACCEPTANCE-AND-EVALS.md').read_text()
for prefix,count,text in [('FR',30,req),('NFR',16,req),('AT',25,eval_text)]:
    pattern = rf'^\| ({prefix}-\d+) \|'
    actual = re.findall(pattern, text, re.M)
    width=3 if prefix=='AT' else 2
    expected={f'{prefix}-{n:0{width}d}' for n in range(1,count+1)}
    check(set(actual)==expected and len(actual)==count, f'{prefix} IDs missing or duplicated')
checks.append('30 functional, 16 nonfunctional and 25 acceptance IDs are complete and unique.')
for path in ROOT.rglob('*.md'):
    if path.name == 'MASTER-DESIGN.md':
        continue
    text=path.read_text()
    check(text.count('```') % 2 == 0, f'Unbalanced code fences: {path.name}')
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if target.startswith(('http:', 'https:', '#', 'mailto:')):
            continue
        target=target.split('#')[0].strip('<>')
        check((path.parent/target).exists(), f'Broken local link in {path.name}: {target}')
checks.append('Markdown fences and local document links checked.')
if errors:
    print('\n'.join('FAIL: '+e for e in errors))
    sys.exit(1)
for item in checks:
    print('PASS: '+item)
print('PASS: Design-package validation complete; no implementation/runtime claims implied.')
