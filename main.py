import argparse
import sys
from pipeline.file_watcher.watcher import watcher

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _cmd_watch(args):

    run_date = args.date
    if run_date:
        print(f"Starting watcher for date: {run_date}")
    else:        
        None
    watcher(run_date = run_date)
    return 0
            

def _build_parser():
    parser =  argparse.ArgumentParser('python main.py')
    sub = parser.add_subparsers(dest='command', required = True)

    p_watch = sub.add_parser('watch', help='start watcher')
    p_watch.add_argument('--date', required=False, default=None)
    p_watch.set_defaults(func=_cmd_watch)
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())