"""Offline extraction contract evaluator; never grants physical qualification."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def parse(answer, normalize=False):
    if normalize:
        answer = answer.strip()
        match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', answer, re.DOTALL)
        if match:
            answer = match[1]
    obj = json.loads(answer, object_pairs_hook=unique)
    if obj == {'abstain': True} and type(obj.get('abstain')) is bool:
        return obj
    if not isinstance(obj, dict) or set(obj) != {'project', 'status', 'owner', 'budget'}:
        raise ValueError('invalid fields')
    if not isinstance(obj['project'], str) or not obj['project'].strip():
        raise ValueError('invalid project')
    if obj['owner'] is not None and (not isinstance(obj['owner'], str) or not obj['owner'].strip()):
        raise ValueError('invalid owner')
    if normalize:
        for key in ('project', 'status', 'owner'):
            if isinstance(obj[key], str):
                obj[key] = obj[key].strip()
        if isinstance(obj['status'], str):
            obj['status'] = obj['status'].casefold()
    if obj['status'] not in ('active', 'paused', 'cancelled', None):
        raise ValueError('invalid status')
    budget = obj['budget']
    if budget is not None and (type(budget) not in (int, float) or not math.isfinite(budget) or budget < 0):
        raise ValueError('invalid budget')
    return obj


def evaluate(workload, trials):
    cases = {c['id']: c for c in workload['cases']}
    expected_counts = {key: workload['repeats'] for key in cases}
    complete = Counter(t['case_id'] for t in trials) == expected_counts and all(t['outcome'] == 'completed' for t in trials)
    rows = []
    for trial in trials:
        case = cases[trial['case_id']]
        raw_valid = False
        try:
            parse(trial['answer'])
            raw_valid = True
        except (ValueError, TypeError):
            pass
        try:
            obj = parse(trial['answer'], normalize=True) if trial['outcome'] == 'completed' else None
        except (ValueError, TypeError):
            obj = None
        abstained = obj == {'abstain': True}
        accepted = obj is not None and not abstained
        correct = obj == case['expected_json']
        rows.append({'case_id':case['id'], 'id':trial['id'], 'raw_schema_valid':raw_valid,
                     'accepted':accepted, 'abstained':abstained, 'correct':correct,
                     'normalized':obj, 'critical':case.get('critical',False),
                     'answerable':case['expected_json'] != {'abstain':True}})
    accepted = [r for r in rows if r['accepted']]
    answerable_total = sum(c['expected_json'] != {'abstain':True} for c in cases.values()) * workload['repeats']
    coverage = sum(r['accepted'] and r['answerable'] for r in rows) / answerable_total
    accuracy = sum(r['correct'] for r in accepted) / len(accepted) if accepted else 0
    unsupported_ok = all(r['abstained'] for r in rows if not r['answerable'])
    critical_errors = [r['id'] for r in rows if r['critical'] and r['accepted'] and not r['correct']]
    policy = workload['acceptance']
    return {'raw_schema_valid':sum(r['raw_schema_valid'] for r in rows),'total':len(rows),
            'normalized_exact_correct':sum(r['correct'] for r in rows),
            'accepted':len(accepted),'accepted_correct':sum(r['correct'] for r in accepted),
            'answerable_coverage':coverage,'accepted_accuracy':accuracy,
            'unsupported_all_abstain':unsupported_ok,'critical_accepted_errors':critical_errors,
            'all_trials_complete':complete,
            'experimental_contract_pass':complete and coverage >= policy['min_answerable_coverage']
                and accuracy >= policy['min_accepted_accuracy'] and unsupported_ok and not critical_errors,
            'physical_device_qualified':False,'peak_stack_bytes':None,'rows':rows}


def baseline(case):
    # Deliberately conservative: only a complete, anchored key/value record.
    # All free prose abstains. No inference from test expectations.
    match = re.fullmatch(r'Project: ([^\n]+)\nStatus: (active|paused|cancelled)\nOwner: ([^\n]+)\nBudget: ([0-9]+(?:\.[0-9]+)?)', case['document'])
    if not match or match[1] != case['target']:
        return {'abstain':True}
    return {'project':match[1],'status':match[2],'owner':match[3], 'budget':float(match[4])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workload', type=Path, required=True)
    parser.add_argument('--results', type=Path, nargs='*', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    workload = json.loads(args.workload.read_text())
    report = {}
    for path in args.results:
        result = json.loads(path.read_text())
        if result['workload_sha256'] != hashlib.sha256(args.workload.read_bytes()).hexdigest():
            parser.error('result/workload hash mismatch')
        report[result['model_file']] = evaluate(workload,result['trials'])
    trials = [{'id':f'{c["id"]}-{r}', 'case_id':c['id'], 'outcome':'completed',
               'answer':json.dumps(baseline(c))} for c in workload['cases'] for r in range(workload['repeats'])]
    report['deterministic-key-value-baseline'] = evaluate(workload,trials)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    for name, result in report.items():
        print(name, json.dumps({k:v for k,v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
