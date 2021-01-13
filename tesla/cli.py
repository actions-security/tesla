#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Console script for tesla."""
import sys

from tesla.main import Tesla

if __name__ == "__main__":
    tesla = Tesla()
    tesla.setup()
    sys.exit(tesla.run())  # pragma: no cover
