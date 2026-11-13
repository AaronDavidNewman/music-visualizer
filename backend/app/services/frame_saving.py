"""How the pictures are saved: the pictures of a file are independent of each other, so they are drawn and encoded on a few threads (numpy and the PNG encoder
release the interpreter lock for their heavy work), and the files are the same whatever the number of threads."""

import os

SAVE_WORKERS = max(1, min(4, os.cpu_count() or 1))
