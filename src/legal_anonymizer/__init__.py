"""Reversible anonymization of Romanian and English legal documents."""

import logging
import os

# Quiet output: no progress bars and no warnings from the model libraries.
# This must run before `transformers` and `torch` are imported.
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").setLevel(logging.ERROR)

__version__ = "0.1.0"
