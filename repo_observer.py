"""
Repo Observer

It checks for new commits to the master repo, and will notify the dispatcher of
the latest commit ID, so the dispatcher can dispatch the tests against this
commit ID. This has been simplified to only dispatch the latest commit ID to the dispatcher
& not subsequent commit IDs. This will continuously poll the repository to check for any new commits. Usually, a 
typical repo observer will receive notifications from the Repository, but some VCS systems do not have built in
notification systems.
"""
import argparse
import os
import re
import socket
import socketserver
import subprocess
import sys
import time

from utils import communicate
from exceptions import RepoObserverError
from logger import logger

def poll():
    """
    Repo Observer poll function that communicates with the dispatcher server to send tests that are found
    on the repository on new changes commited to the repo. This will watch the repo every 5 seconds for any
    new commit that is made & make a dispatch to the dispatch server to initiate running of new tests.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--dispatcher-server", help="dispatcher host:port , by default it uses localhost:8000",
                        default="localhost:8000", 
                        action="store")
    parser.add_argument("--repo", metavar="REPO", type=str, help="path to the repository to observe")
    parser.add_argument("--poll", help="how long to keep polling repository", default=5, type=int)
    parser.add_argument("--branch", help="which branch to run tests against", default="master", type=str)

    args = parser.parse_args()
    dispatcher_host, dispatcher_port = args.dispatcher_server.split(":")

    while True:
        try:
            # call the bash script that will update the repo and check
            # for changes. If there's a change, it will drop a .commit_id file
            # with the latest commit in the current working directory
            logger.info(f"cloning repo {args.repo}")
            subprocess.check_output(["./scripts/update_repo.sh", args.repo, args.branch])
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update & check repo {args.repo}, err: {e.output}")
            raise RepoObserverError(f"Could not update & check repository. Err: {e.output}")

        if os.path.isfile("files/.commit_id"):
            # great, we have a change! let's execute the tests
            # First, check the status of the dispatcher server to see
            # if we can send the tests
            try:
                response = communicate(dispatcher_host, int(dispatcher_port), "status")
            except socket.error as e:
                logger.error(f"Dispather Server Contact error. Is Dispatcher running? err: {e}")
                raise RepoObserverError(f"Could not contact dispatcher {e}")
            
            if response == "OK":
                # Dispatcher is available
                commit = ""
                
                with open("files/.commit_id") as commit_file:
                    commit = commit_file.readline
                
                response = communicate(dispatcher_host, int(dispatcher_port), f"dispatch:{commit}")

                if response != "OK":
                    logger.error(f"Failed to dispatch test to dispatcher. Is Dispatcher OK? err: {response}")
                    raise RepoObserverError(f"Could not dispatch test: {response}")
                logger.info(f"Dispatched tests for {args.repo}!")
            else:
                # Dispatcher has an issue
                raise RepoObserverError(f"Could not dispatch test {response}")
        
        time.sleep(args.poll)

if __name__ == "__main__":
    poll()