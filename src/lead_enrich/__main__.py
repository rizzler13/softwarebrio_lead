"""Allow running with `python -m lead_enrich`."""

import asyncio

from lead_enrich.main import main

asyncio.run(main())
