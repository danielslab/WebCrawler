__version__ = '0.2.0'

import os
import sys
import logging
import argparse
from .core import WebCrawler
from mail_helper import MailgunHelper
from .helpers import color_logging

def main():
    """ parse command line options and run commands.
    """
    parser = argparse.ArgumentParser(
        description='A web crawler for testing website links validation.')

    parser.add_argument(
        '-V', '--version', dest='version', action='store_true',
        help="show version")
    parser.add_argument(
        '--log-level', default='INFO',
        help="Specify logging level, default is INFO.")
    parser.add_argument(
        '--seeds', default='http://debugtalk.com',
        help="Specify crawl seed url(s), several urls can be specified with pipe; \
              if auth needed, seeds can be specified like user1:pwd1@url1|user2:pwd2@url2")
    parser.add_argument(
        '--include-hosts', help="Specify extra hosts to be crawled.")
    parser.add_argument(
        '--cookies', help="Specify cookies, several cookies can be joined by '|'. \
            e.g. 'lang:en,country:us|lang:zh,country:cn'")
    parser.add_argument(
        '--crawl-mode', default='BFS', help="Specify crawl mode, BFS or DFS.")
    parser.add_argument(
        '--max-depth', default=5, type=int, help="Specify max crawl depth.")
    parser.add_argument(
        '--concurrency', help="Specify concurrent workers number.")
    parser.add_argument(
        '--job-url', default='0', help="Specify jenkins job url.")
    parser.add_argument(
        '--build-number', default='0', help="Specify jenkins build number.")

    parser.add_argument('--save-results', dest='save_results', action='store_true')
    parser.add_argument('--not-save-results', dest='save_results', action='store_false')
    parser.set_defaults(save_results=False)

    parser.add_argument("--grey-user-agent",
                        help="Specify grey environment header User-Agent.")
    parser.add_argument("--grey-traceid",
                        help="Specify grey environment cookie traceid.")
    parser.add_argument("--grey-view-grey",
                        help="Specify grey environment cookie view_gray.")

    mailer = MailgunHelper(parser)
    args = parser.parse_args()

    if args.version:
        print(__version__)
        exit(0)

    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level)
    color_logging("args: %s" % args)

    main_crawler(args, mailer)

def main_crawler(args, mailer=None):
    include_hosts = args.include_hosts.split(',') if args.include_hosts else []
    cookies_list = args.cookies.split('|') if args.cookies else ['']
    job_url = args.job_url
    build_number = args.build_number
    logs_folder = os.path.join(os.getcwd(), "logs", '{}'.format(build_number))

    web_crawler = WebCrawler(args.seeds, include_hosts, logs_folder)

    # set grey environment
    if args.grey_user_agent and args.grey_traceid and args.grey_view_grey:
        web_crawler.set_grey_env(args.grey_user_agent, args.grey_traceid, args.grey_view_grey)

    canceled = False
    try:
        for cookies_str in cookies_list:
            cookies_str_list = cookies_str.split(',')
            cookies = {}
            for cookie_str in cookies_str_list:
                if ':' not in cookie_str:
                    continue
                key, value = cookie_str.split(':')
                cookies[key.strip()] = value.strip()

            web_crawler.start(
                cookies,
                args.crawl_mode,
                args.max_depth,
                args.concurrency
            )

        if mailer and mailer.config_ready:
            subject = "test reuslt of %s" % args.seeds
            jenkins_log_url = "{}/{}/console".format(job_url, build_number)
            html_content = web_crawler.gen_mail_html_content(jenkins_log_url)
            mailer.send_mail(subject, html=html_content)
    except KeyboardInterrupt:
        canceled = True
        color_logging("Canceling...", color='red')
    finally:
        web_crawler.print_result(canceled, save_visited_urls=args.save_results)
