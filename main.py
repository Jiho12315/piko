"""피코(Piko) 진입점. 앱 조립은 piko.app이 담당한다."""

import sys

from piko.app import run

if __name__ == "__main__":
    sys.exit(run(sys.argv))
