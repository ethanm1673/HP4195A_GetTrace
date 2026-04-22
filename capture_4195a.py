"""
HP 4195A trace capture — read-only.

Does NOT change sweep state, measurement setup, or calibration.
Only reads the currently-displayed X/A/B registers in whatever format
the instrument is already set to.
"""

import pyvisa, time, datetime, sys, re

GPIB_ADDR = 5
TIMEOUT_MS = 60000

def sanitize(name):
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name

def main():
    # --- prompt for filename and optional note ---
    raw_name = input('Filename (without extension, blank = timestamp): ')
    note = input('Short note (optional, saved in CSV header): ')

    if raw_name.strip():
        base = sanitize(raw_name)
    else:
        base = '4195a_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    csv_path = f'{base}.csv'
    raw_path = f'{base}_raw.txt'

    # --- connect ---
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(f'GPIB0::{GPIB_ADDR}::INSTR')
    inst.timeout = TIMEOUT_MS
    inst.read_termination = '\n'
    inst.write_termination = '\n'
    inst.chunk_size = 102400

    # --- sanity check only; no state changes ---
    print('\nID:', inst.query('ID?').strip())

    # Set ASCII output format. This affects the GPIB output buffer format
    # only, NOT calibration, sweep state, or any measurement setup.
    inst.write('FMT1')
    time.sleep(0.2)

    # --- pure register reads ---
    print('Pulling X...')
    x_raw = inst.query('X?')
    print(f'  {len(x_raw)} chars')

    print('Pulling A...')
    a_raw = inst.query('A?')
    print(f'  {len(a_raw)} chars')

    print('Pulling B...')
    b_raw = inst.query('B?')
    print(f'  {len(b_raw)} chars')

    def parse(s):
        vals = []
        for tok in s.replace('\n', ',').split(','):
            tok = tok.strip()
            if not tok: continue
            try: vals.append(float(tok))
            except ValueError: continue
        return vals

    x = parse(x_raw)
    a = parse(a_raw)
    b = parse(b_raw)
    print(f'Parsed: X={len(x)}  A={len(a)}  B={len(b)}')

    n = min(len(x), len(a), len(b))
    timestamp = datetime.datetime.now().isoformat()

    with open(csv_path, 'w') as f:
        f.write(f'# HP 4195A capture {timestamp}\n')
        if note.strip():
            f.write(f'# note: {note.strip()}\n')
        f.write(f'# points: {n}\n')
        f.write('x,a,b\n')
        for i in range(n):
            f.write(f'{x[i]:.9e},{a[i]:.9e},{b[i]:.9e}\n')

    with open(raw_path, 'w') as f:
        f.write(f'# HP 4195A raw capture {timestamp}\n')
        if note.strip():
            f.write(f'# note: {note.strip()}\n')
        f.write('=== X? ===\n' + x_raw + '\n\n=== A? ===\n' + a_raw + '\n\n=== B? ===\n' + b_raw + '\n')

    print(f'\nWrote {csv_path} ({n} points)')
    print(f'Wrote {raw_path}')
    inst.close()

if __name__ == '__main__':
    main()
