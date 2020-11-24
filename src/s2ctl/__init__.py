import asyncio
import sys

from s2ctl import cmd_context, cmd_metainfo, cmd_network, cmd_project, cmd_server, cmd_sshkey, cmd_task  # noqa: F401

# Fix for RuntimeError: Event loop is closed
# https://github.com/encode/httpx/issues/914
if sys.version_info >= (3, 8) and sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
