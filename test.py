#!/usr/bin/env python2

#!/usr/bin/env python2

from __future__ import print_function

import time
from openbci_collector import *

collector = OpenBCICollector(extra_process = print)

collector.start_bg_collection()

# start training here

collector.tag_it('hand')

# stop training

collector.tag_it(None)

# time.sleep(10)


collector.stop_bg_collection()
