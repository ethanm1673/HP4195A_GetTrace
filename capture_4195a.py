"""
HP 4195A trace capture over GPIB.
Pulls X-axis + channel A + channel B registers as ASCII, writes to CSV
with a sidecar state file capturing instrument config.
"""

import pyvisa
import time
import datetime
import sys

GPIB_ADDR = 17          # 4195A default
TIMEOUT_MS = 60000      # 60s — ASCII transfer of 400 points is slow

def main():
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    print('VISA resources found:', resources)

    inst = rm.open_resource(f'GPIB0::{GPIB_ADDR}::INSTR')
    inst.timeout = TIMEOUT_MS
    inst.read_termination = '\n'
    inst.write_termination = '\n'
    inst.chunk_size = 102400

    def q(cmd):
        return inst.query(cmd).strip()

    def w(cmd):
        inst.write(cmd)
        time.sleep(0.05)

    # --- sanity ---
    ident = q('ID?')
    print('ID:', ident)

    # --- grab instrument state ---
    # wrap each query individually so one failed query doesn't abort everything
    def try_q(cmd, default='?'):
        try:
            return q(cmd)
        except Exception as e:
            return f'<err: {e}>'

    state = {
        'timestamp':  datetime.datetime.now().isoformat(),
        'id':         ident,
        'function':   try_q('FNC?'),
        'start':      try_q('START?'),
        'stop':       try_q('STOP?'),
        'center':     try_q('CENTER?'),
        'span':       try_q('SPAN?'),
        'nop':        try_q('NOP?'),
        'rbw':        try_q('RBW?'),
        'power':      try_q('POWER?'),
        'sweep_time': try_q('ST?'),
        'a_format':   try_q('AFMT?'),
        'b_format':   try_q('BFMT?'),
    }

    print('\nInstrument state:')
    for k, v in state.items():
        print(f'  {k}: {v}')

    # --- stop sweeping, set ASCII output ---
    w('SWM2')    # single-sweep mode (halts continuous)
    w('FMT1')    # ASCII output format
    time.sleep(0.2)

    # --- pull arrays ---
    print('\nPulling X register...')
    x_raw = q('X?')
    print(f'  got {len(x_raw)} chars')

    print('Pulling A register...')
    a_raw = q('A?')
    print(f'  got {len(a_raw)} chars')

    print('Pulling B register...')
    b_raw = q('B?')
    print(f'  got {len(b_raw)} chars')

    def parse(s):
        # 4195A sometimes prefixes with a header like "DATA" or returns
        # values separated by commas. Strip anything non-numeric from start.
        vals = []
        for tok in s.replace('\n', ',').split(','):
            tok = tok.strip()
            if not tok:
                continue
            try:
                vals.append(float(tok))
            except ValueError:
                # skip header tokens
                continue
        return vals

    x_vals = parse(x_raw)
    a_vals = parse(a_raw)
    b_vals = parse(b_raw)

    print(f'\nParsed: X={len(x_vals)}  A={len(a_vals)}  B={len(b_vals)} points')

    if not (len(x_vals) == len(a_vals) == len(b_vals)):
        print('WARNING: array lengths differ. Check raw output in *_raw.txt')
        # dump raw for debugging
        with open('4195a_raw_debug.txt', 'w') as f:
            f.write('=== X? ===\n' + x_raw + '\n\n')
            f.write('=== A? ===\n' + a_raw + '\n\n')
            f.write('=== B? ===\n' + b_raw + '\n')

    # --- write CSV + sidecar ---
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = f'4195a_{stamp}.csv'
    state_path = f'4195a_{stamp}_state.txt'

    n = min(len(x_vals), len(a_vals), len(b_vals))
    with open(csv_path, 'w') as f:
        f.write(f'# HP 4195A capture {state["timestamp"]}\n')
        f.write(f'# function={state["function"]}  nop={state["nop"]}\n')
        f.write(f'# start={state["start"]}  stop={state["stop"]}\n')
        f.write(f'# a_format={state["a_format"]}  b_format={state["b_format"]}\n')
        f.write('x,a,b\n')
        for i in range(n):
            f.write(f'{x_vals[i]:.9e},{a_vals[i]:.9e},{b_vals[i]:.9e}\n')

    with open(state_path, 'w') as f:
        for k, v in state.items():
            f.write(f'{k}: {v}\n')

    print(f'\nWrote {csv_path} ({n} points)')
    print(f'Wrote {state_path}')

    inst.close()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)
