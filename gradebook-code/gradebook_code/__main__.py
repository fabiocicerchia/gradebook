"""Entry point for `python -m gradebook_code`.

The tool used to be a single file that editors and CI ran as a script. It is a
package now, so this is the equivalent: the plugins and workflows call
`python3 -m gradebook_code` and get the same main().
"""

import sys

from . import main

if __name__ == "__main__":
    sys.exit(main())
