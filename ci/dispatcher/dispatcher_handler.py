"""
Dispatch Handler

This is responsible for handling all requests that come in for the dispatch server
"""

import socketserver
import re
import os

from ci.logger import logger
from .utils import dispatch_tests


class DispatcherHandler(socketserver.BaseRequestHandler):
    """
    Inherits from socketserver's BaseRequestHandler

    This overrides the hande method to execute the various commands that come in from connections to the
    dispatch server.

    Compilation of the command from a Regex if first used to check if there are commands to execute
    & if nothing compiles, returns a response stating an invalid command was requested

    It then proceeds to handle the commands if the command is available & can be handled

    4 Commands are handled

    status:
    :cvar command_re: Compiled Regex of the command to handle for incoming request
    :cvar BUF_SIZE: buffer size
    """

    command_re = re.compile(r"([b])'(\w+)(:.+)*'")
    BUF_SIZE = 1024

    def handle(self):
        self.data = self.request.recv(self.BUF_SIZE).strip()
        self.command_groups = self.command_re.match(f"{self.data}")

        self.commands = {
            "status": self.check_status,
            "register": self.register,
            "dispatch": self.dispatch,
        }

        if not self.command_groups:
            self.invalid_command()
            return

        command = self.command_groups.group(2)

        # Handle commands, if none match, handle invalid command
        self.commands.get(command, self.invalid_command)()

    def invalid_command(self):
        self.request.sendall(b"Invalid command")

    def check_status(self):
        """
        Checks the status of the dispatcher server
        """
        logger.info("Checking Dispatch Server Status")
        self.request.sendall(b"OK")

    def register(self):
        """
        registers new test runners to the runners pool
        """
        address = self.command_groups.group(3)
        host, port = re.findall(r":(\w*)", address)
        runner = {"host": host, "port": port}
        logger.info(f"Registering new test runner {host}:{port}")
        self.server.runners.append(runner)
        self.request.sendall(b"OK")

    def dispatch(self):
        """
        dispatch command is used to dispatch a commit against a test runner. When the repo
        observer sends this command as 'dispatch:<commit_id>'. The dispatcher parses the commit_id
        & sends it to a test runner
        """
        logger.info("Dispatching to test runner")
        commit_id_and_branch = self.command_groups.group(3)[1:]

        c_and_b = commit_id_and_branch.split(":")
        commit_id = c_and_b[0]
        branch = c_and_b[1]

        logger.debug(f"Received commit_id {commit_id}")

        if not self.server.runners:
            self.request.sendall(b"No runners are registered")
        else:
            # we can dispatch tests, we have at least 1 test runner available
            self.request.sendall(b"OK")
            dispatch_tests(self.server, commit_id, branch)
