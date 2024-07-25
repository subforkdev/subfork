#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains commandline functions and classes.
"""

import os
import sys

import subfork.config as config

from subfork import util
from subfork.version import __prog__, __version__


def parse_args():
    """Command line argument parser."""

    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="which", help="which command to run")
    parser.add_argument(
        "--host",
        type=str,
        metavar="HOST",
        help="site domain",
        default=config.HOST,
    )
    parser.add_argument(
        "--port",
        type=int,
        metavar="PORT",
        help="port number",
        default=config.PORT,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    # new site template generator
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument(
        "-t",
        "--templates",
        default="templates",
        help="path to folder containing html template files",
    )
    create_parser.add_argument(
        "-s",
        "--static",
        default="static",
        help="path to folder containing static files",
    )
    create_parser.add_argument(
        "-d",
        "--domain",
        default=config.HOST,
        help="site domain",
    )
    create_parser.add_argument(
        "--noext",
        action="store_true",
        help="remove .html ext from routes",
        default=False,
    )

    # build arg parser
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument(
        "template",
        nargs="?",
        default=config.config_file,
        help="path to subfork.yml file",
    )
    build_parser.add_argument(
        "-t",
        "--target",
        metavar="BUILDDIR",
        help="build target directory",
    )

    # dev server parser
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "template",
        nargs="?",
        default=config.config_file,
        help="path to subfork.yml file",
    )
    run_parser.add_argument(
        "--host",
        type=str,
        metavar="HOST",
        help="dev server host",
        default="localhost",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        metavar="PORT",
        help="dev server port",
        default=8080,
    )

    # deploy arg parser
    deploy_parser = subparsers.add_parser("deploy")
    deploy_parser.add_argument(
        "template",
        nargs="?",
        default=config.config_file,
        help="path to subfork.yml file",
    )
    deploy_parser.add_argument(
        "-c",
        "--comment",
        metavar="COMMENT",
        help="use given comment as deployment description",
    )
    deploy_parser.add_argument(
        "--release",
        action="store_true",
        help="release deployed version",
        default=False,
    )
    deploy_parser.add_argument(
        "--force",
        action="store_true",
        help="force deployment",
        default=False,
    )

    # worker arg parser
    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument(
        "workers",
        nargs="*",
        metavar="WORKERS",
        help="specify which workers from config file to run",
    )
    worker_parser.add_argument(
        "--func",
        default=None,
        help="import path to worker function",
    )
    worker_parser.add_argument(
        "--limit",
        default=config.TASK_RETRY_LIMIT,
        type=int,
        help="task failure retry limit",
    )
    worker_parser.add_argument(
        "--queue",
        default=None,
        help="the name of the task queue",
    )
    worker_parser.add_argument(
        "--wait",
        metavar="SECONDS",
        type=int,
        help="queue polling interval",
        default=config.WAIT_TIME,
    )

    args = parser.parse_args()

    return args, parser


def main():
    """Main thread."""
    args, parser = parse_args()

    util.check_version()

    if args.which == "deploy":
        if not args.comment:
            print("--comment is required")
            return 2

        from subfork import deploy

        client = util.get_client(args.host, args.port)
        deploy.deploy(
            client,
            template_file=os.path.abspath(args.template),
            comment=args.comment,
            release=args.release,
            force=args.force,
        )

    elif args.which == "build":
        from subfork import build

        template_file = os.path.abspath(args.template)
        build.build(template_file, args.target)

    elif args.which == "create":
        from subfork import build

        template_file = os.path.join(os.getcwd(), "subfork.yml")

        build.create_template(
            filepath=template_file,
            domain=args.domain,
            access_key="${SUBFORK_ACCESS_KEY}",
            secret_key="${SUBFORK_SECRET_KEY}",
            minimize=False,
            static_folder=args.static,
            template_folder=args.templates,
            templates=util.get_templates(args.templates, args.noext),
        )

    elif args.which == "run":
        from subfork import app

        if not args.template:
            print("template file is required")
            return 2
        elif not os.path.isfile(args.template):
            print("file not found: %s" % args.template)
            return 2

        template_file = os.path.abspath(args.template)
        client = util.get_client(host=config.HOST, port=config.PORT)

        return app.run(
            client=client,
            template=template_file,
            host=args.host,
            port=args.port,
        )

    elif args.which == "worker":
        from subfork.worker import run_workers

        client = util.get_client(args.host, args.port)
        worker_config = config.get_config("workers")

        if args.queue and args.func:
            worker_config = {
                "cli": {
                    "queue": args.queue,
                    "function": args.func,
                    "limit": args.limit,
                    "wait_time": args.wait,
                }
            }
            return run_workers(client, worker_config)
        elif args.workers:
            if not config.WORKERS:
                print("no workers found in %s" % args.template)
                return 2
            else:
                worker_config = dict(
                    (name, worker_config)
                    for (name, worker_config) in config.WORKERS.items()
                    if name in args.workers
                )
                return run_workers(client, worker_config)
        elif config.WORKERS:
            return run_workers(client, config.WORKERS)
        else:
            parser.print_help()

    else:
        print("invalid command: %s" % args.which)
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
