"""支持 ``python -m chartread`` 运行命令行。"""

import sys

from chartread.cli import main

if __name__ == "__main__":
    sys.exit(main())
