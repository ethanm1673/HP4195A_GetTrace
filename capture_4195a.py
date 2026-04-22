"""HP 4195A minimal trace capture."""

import pyvisa, time, datetime, sys

GPIB_ADDR = 5
TIMEOUT_MS = 60000

def main():
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(f'GPIB0::{GPIB_ADDR}::INSTR')
    inst.timeout = TIMEOUT_MS
    inst.read_termination = '\n'
    inst.write_termination = '\n'
    inst.chunk_size = 102400

    print('ID:', inst.query('ID?').strip())

    inst.write('SWM2')
    time.sleep(0.1)
    inst.write('FMT1')
    time.sleep(0.2)

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

    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = f'4195a_{stamp}.csv'
    n = min(len(x), len(a), len(b))
    with open(path, 'w') as f:
        f.write('x,a,b\n')
        for i in range(n):
            f.write(f'{x[i]:.9e},{a[i]:.9e},{b[i]:.9e}\n')

    # also dump raw for debugging
    with open(f'4195a_{stamp}_raw.txt', 'w') as f:
        f.write('=== X? ===\n' + x_raw + '\n\n=== A? ===\n' + a_raw + '\n\n=== B? ===\n' + b_raw + '\n')

    print(f'Wrote {path} ({n} points)')
    inst.close()

if __name__ == '__main__':
    main()
