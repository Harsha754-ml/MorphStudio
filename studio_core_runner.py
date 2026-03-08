import sys
import json
from studio_core import StudioCore

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Error: no JSON argument provided', flush=True)
        sys.exit(1)

    try:
        data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f'Error: invalid JSON: {e}', flush=True)
        sys.exit(1)

    quality_map = {
        'Draft': 'l',
        'HD': 'm',
        'Full HD': 'k',
        '4K': 'p',
    }
    quality = quality_map.get(data.get('quality', 'Draft'), 'l')

    def log(line):
        print(line, end='', flush=True)

    try:
        success = StudioCore.run_render(
            data['global_params'],
            data['assets'],
            quality,
            log,
        )
    except Exception as e:
        print(f'Error during render: {e}', flush=True)
        sys.exit(1)

    sys.exit(0 if success else 1)
