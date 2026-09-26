"""Run real two-turn conversations in an explicitly selected iOS Simulator.

Manual rubric review is required. No physical qualification or speech claim.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def prompt_for(messages, template):
    # llama-simple adds BOS for LFM2; Qwen3.5 adds none.
    prompt = ''.join('<|im_start|>' + m['role'] + '\n' + m['content'] + '<|im_end|>\n' for m in messages)
    prompt += '<|im_start|>assistant\n'
    if template == 'qwen3-no-thinking':
        prompt += '<think>\n\n</think>\n\n'
    return prompt


def answer_from(raw, prompt, template):
    text = raw.decode('utf-8')
    echo = ('<|startoftext|>' if template == 'lfm2' else '') + prompt
    if not text.startswith(echo):
        raise ValueError('prompt echo mismatch')
    return text[len(echo):].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary','model','workload','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--simulator',required=True)
    parser.add_argument('--template',choices=['lfm2','qwen3-no-thinking'],required=True)
    args = parser.parse_args()
    if digest(args.model) != args.sha256:
        parser.error('model hash mismatch')
    build = subprocess.run(['xcrun','vtool','-show-build',str(args.binary)],capture_output=True,text=True,check=True).stdout
    if 'platform IOSSIMULATOR' not in build:
        parser.error('not an iOS simulator binary')
    inventory = json.loads(subprocess.run(['xcrun','simctl','list','devices','-j'],capture_output=True,text=True,check=True).stdout)
    devices = [(r,d) for r,ds in inventory['devices'].items() for d in ds if d['udid']==args.simulator and d['state']=='Booted']
    if len(devices)!=1:
        parser.error('known booted simulator required')
    workload = json.loads(args.workload.read_text())
    args.output.mkdir(parents=True,exist_ok=False)
    trials=[]
    for scenario in workload['scenarios']:
        messages=[{'role':'system','content':scenario['system']}]
        for index,turn in enumerate(scenario['turns']):
            tid=f'{scenario["id"]}-{index}'
            messages.append({'role':'user','content':turn['user']})
            prompt=prompt_for(messages,args.template)
            command=['xcrun','simctl','spawn',args.simulator,str(args.binary),'-m',str(args.model),'-ngl','0','-n',str(workload['max_output_tokens']),prompt]
            try:
                run=subprocess.run(command,capture_output=True,timeout=45)
                raw,err=run.stdout,run.stderr
                try:
                    answer=answer_from(raw,prompt,args.template)
                    outcome='completed' if run.returncode==0 and answer else 'failed'
                except ValueError:
                    answer,outcome='','failed'
            except subprocess.TimeoutExpired as exc:
                # Stop the entire run: simctl cancellation may leave the child.
                (args.output/f'{tid}.stdout').write_bytes(exc.stdout or b'')
                (args.output/f'{tid}.stderr').write_bytes(exc.stderr or b'')
                raise SystemExit('Timeout: inspect simulator child before continuing; partial logs retained')
            (args.output/f'{tid}.stdout').write_bytes(raw)
            (args.output/f'{tid}.stderr').write_bytes(err)
            row={'id':tid,'lane':scenario['lane'],'user':turn['user'],'answer':answer,'outcome':outcome,'rubric':turn['rubric'],'critical':turn['critical']}
            trials.append(row)
            print(json.dumps(row),flush=True)
            # Follow-up sees the actual generated reply, not an ideal answer.
            if outcome!='completed':
                break
            messages.append({'role':'assistant','content':answer})
    result={'schema':'beanfit.product-conversations.receipt.v1','recorded_at':datetime.now(timezone.utc).isoformat(),
            'evidence_kind':'simulator','model_file':args.model.name,'model_sha256':args.sha256,'model_bytes':args.model.stat().st_size,
            'binary_sha256':digest(args.binary),'workload_sha256':digest(args.workload),'template':args.template,
            'simulator':devices[0][1],'runtime':devices[0][0],'sampling':'greedy','backend':'CPU; no Metal/Accelerate',
            'context':'prompt tokens + 192 output tokens - 1; reload model and replay conversation each turn',
            'physical_device_qualified':False,'speech_audio_tested':False,'peak_stack_bytes':None,'trials':trials}
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
