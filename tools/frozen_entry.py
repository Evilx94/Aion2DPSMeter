"""Windows entry point: no external Python is used by the frozen application."""
import sys,os,multiprocessing
if sys.stdout is None:sys.stdout=open(os.devnull,'w')
if sys.stderr is None:sys.stderr=open(os.devnull,'w')
if __name__=='__main__':
    multiprocessing.freeze_support()
    if '--self-test' in sys.argv:
        from meter.distribution_check import run
        at=sys.argv.index('--self-test');raise SystemExit(run(sys.argv[at+1],capture='--check-capture' in sys.argv))
    from meter.__main__ import main
    raise SystemExit(main())
