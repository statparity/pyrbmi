# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""pyrbmi: Python implementation of reference-based multiple imputation.

This package provides regulatory-compliant multiple imputation methods
for clinical trials, with numerical parity to R's rbmi package.
"""

from pyrbmi.covariance import CovarianceStructure
from pyrbmi.data import RBMIDataset
from pyrbmi.imputer import Imputer
from pyrbmi.models import MMRM, MMRMConvergenceError
from pyrbmi.pool import PooledResults, pool
from pyrbmi.strategy import Strategy
from pyrbmi.validators import RBMIDataError, validate_columns, validate_no_missing_baseline

__version__ = "0.0.1.dev0"

__all__ = [
    "CovarianceStructure",
    "MMRM",
    "MMRMConvergenceError",
    "RBMIDataset",
    "RBMIDataError",
    "Imputer",
    "Strategy",
    "pool",
    "PooledResults",
    "validate_columns",
    "validate_no_missing_baseline",
]
