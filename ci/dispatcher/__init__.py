"""
This is the test dispatcher.

It will dispatch tests against any registered test runners when the repo
observer sends it a 'dispatch' message with the commit ID to be used. It
will store results when the test runners have completed running the tests and
send back the results in a 'results' messagee

It can register as many test runners as you like. To register a test runner,
be sure the dispatcher is started, then start the test runner.
"""
import time
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread

from ci.logger import logger
from ci.utils import communicate
from .utils import dispatch_tests

from .threading_tcp_server import ThreadingTCPServer
from .dispatcher_handler import DispatcherHandler


def runner_checker(server):
    """
    This will run a check(ping) against each test runner server to check if they are still responsive.
    If any of the test runners go down or become unresponsive, the runner is removed from the connection pool
    & the commit_id is dispatched to a responsive test runner. The commit_id is logged onto the pending_commits
    
    :param server: dispatcher server instance
    """

    def manage_commit_lists(runner):
        for commit, assigned_runner in server.dispathed_commits.items():
            if assigned_runner == runner:
                del server.dispatched_commits[commit]
                server.pending_commits.append(commit)
                break
        server.runners.remove(runner)

    while not server.dead:
        time.sleep(1)

        for runner in server.runners:
            socket(AF_INET, SOCK_STREAM)

            try:
                response = communicate(runner["host"], int(runner["port"]), "ping")

                if response != b"pong":
                    logger.warning(f"Removing runner {runner} from pool")
                    manage_commit_lists(runner)
            except socket.error as e:
                logger.error(f"Failed to communicate with runner {runner}, Err: {e}")
                manage_commit_lists(runner)


def redistribute(server):
    """
    This is used to `redistribute` the commit_ids that are in the pending_commits `queue`(pending_commits list)
    It then calls dispatch_tests if there are pending commits
    """
    while not server.dead:
        for commit in server.pending_commits:
            logger.info(f"Redistributing pending commits {server.pending_commits} ...")
            dispatch_tests(server, commit)
            time.sleep(5)


def dispatcher_server(host, port):
    """
    Entry point to dispatch server
    """

    server = ThreadingTCPServer((host, int(port)), DispatcherHandler)

    logger.info(f"Dispatcher Server running on address {host}:{port}")

    runner_heartbeat = Thread(target=runner_checker, args=(server,))
    redistributor = Thread(target=redistribute, args=(server,))

    try:
        runner_heartbeat.start()
        redistributor.start()

        # Run forever unless stopped
        server.serve_forever()
    except (KeyboardInterrupt, Exception):
        # in case it is stopped or encounters any error
        server.dead = True
        runner_heartbeat.join()
        redistributor.join()
