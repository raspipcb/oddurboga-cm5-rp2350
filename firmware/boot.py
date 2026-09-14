# MicroPython: start the plant controller after reset.
# If startup fails, the traceback is printed and the REPL stays available.

import time

time.sleep_ms(500)

try:
    import main

    main.main()
except Exception:
    import sys

    sys.print_exception(sys.exc_info()[1])
