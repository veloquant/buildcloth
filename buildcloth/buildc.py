from __future__ import absolute_import

from multiprocessing import cpu_count
from buildcloth.makefile import MakefileCloth
from buildcloth.system import BuildSystemGenerator, is_function, narrow_buildsystem

import sys
import argparse
import os
import logging
import subprocess

logger = logging.getLogger(__name__)

def _import_strings():
    """
    Takes no arguments and returns a dictionary mapping identifiers to strings,
    used for variables or dynamic replacement of tokens in strings.
    """

    try:
        from buildc import strings
    except ImportError:
        strings = {}

    if is_function(strings):
        strings = strings()

    if not isinstance(strings, dict):
        logger.critical('strings object is not a dictionary')
        raise TypeError

    return strings

############### function to generate and run buildsystem ###############

def stages(jobs, stages, file, check):
    """
    Main public function to generate and run a
    :class:`~system.BuildSystemGenerator()` build system.
    """

    if os.path.isdir('buildc') or os.path.exists('buildc.py'):
        try:
            from buildc import functions
        except ImportError:
            from buildc import funcs as functions
        else:
            functions = None
    else:
        functions = None

    strings = _import_strings()
    bsg = BuildSystemGenerator(functions)
    bsg.check_method = check

    if functions is None:
        logger.info('no python functions pre-loaded')

    for fn in file:
        if fn.endswith('json'):
            bsg.ingest_json(fn, strings)
        elif fn.endswith('yaml') or fn.endswith('yml'):
            bsg.ingest_yaml(fn, strings)
        else:
            logger.warning('format of {0} is unclear, not parsing'.format(fn))

    bsg.finalize()
    bsg.system.workers(jobs)

    if not stages:
        bsg.system.run()
    else:
        bsg = narrow_buildsystem(stages, bsg.system)
        bsg.system.workers(jobs)
        bsg.run()


############### functions to generate makefiles ###############

## "public" make function.

def make(files, stages):
    m = Makecloth()
    targets = _load_build_specs(files)

    for job in targets:
        target, dependency = _process_make_dependency(job)

        m.target(target, dependency)

        make_jobs = _generate_make_jobs(_collect_make_tasks(job))

        for j in make_jobs:
            m.job(j)

        if 'msg' in job:
            m.msg(job['msg'])
        elif 'message' in job:
            m.msg(job['message'])

    m.write('Makefile')
    logger.info('wrote build system to Makefile')

    logger.info('running make')
    if not stages:
        logger.debug('running make without any targets.')
        subprocess.call('make')
    else:
        logger.debug('building the following targets: {0}.'.format(', '.join(stages)))
        suprocess.call(['make'].extend(stages))

## component functions and processes

def _process_make_dependency(job):
    if 'target' in job:
        target = job['target']

        if 'dep' in job:
            dependency = job['dep']
        if 'deps' in job:
            dependency = job['deps']
        elif 'dependency' in job:
            dependency = job['dependency']
        elif 'd' in job:
            dependency = job['d']
        else:
            dependency = None
    else:
        target = job['stage']
        dependency = None

    return target, dependency

def _collect_make_tasks(job):
    tasks = []
    t = job if 'job' in job or 'cmd' in job else False

    if t is not False:
        tasks.append(t)
    try:
        tasks.update(job['tasks'])
    except KeyError:
        logger.debug('no task list in job dict, continuing.')

    return tasks

def _generate_make_jobs(tasks):
    jobs = []
    for task in tasks:
        if (os.path.isdir('buildc') or os.path.exists('buildc.py') ) and 'job' in task:
            job = 'python -c from buildc import functions ; functions[{0}]({1})'
            if 'args' not in task:
                task['args'] = []

            if isinstance(task['args'], (list, tuple)):
                args = '*' + ', '.join(task['args'])
            elif isinstance(task['args'], dict):
                args = '**' + str(task['args'])

            job.format(task['job'], args)
        elif 'cmd' in task:
            if 'dir' in task:
                if isinstance(task['dir'], list):
                    job = 'cd ' + os.path.sep.join(task['dir'])
                else:
                    job = 'cd ' + task['dir']
            else:
                job = ''

            if isinstance(task['cmd'], list):
                job += '; '.join(task['cmd'])
            else:
                job += '; ' + task['cmd']
                if 'args' in task:
                    job += ' '
                    job += ' '.join(task['args'])

        jobs.append(job)

    return jobs

def _load_build_specs(files):
    targets = []

    strings = _import_strings()

    for fn in files:
        try:
            with open(fn, 'r') as f:
                if fn.endswith('json'):
                    tg = json.load(f)
                    for i in tg:
                        i = BuildSystemGenerator.process_strings(i, strings)
                        if isinstance(i, list):
                            for doc in i:
                                tg.append(i)
                        elif isinstance(i, dict):
                            targets.append(i)
                        else:
                            logger.warning('structure of json file {0}is unclear, ignoring file.'.format(fn))
                elif fn.endswith('yaml') or fn.endswith('yml'):
                    for i in yaml.safe_load_all(f):
                        i = BuildSystemGenerator.process_strings(i, strings)
                        targets.append(i)
                else:
                    logger.warning('format of {0} is unclear, not parsing'.format(fn))
        except OSError:
            logger.warning('{0} is not readable; passing'.format(fn))

    return targets

############### Command Line Interface and main() ###############

def cli_ui():
    parser = argparse.ArgumentParser("'buildc' -- build system tool.")

    parser.add_argument('--log', '-l', action='store', default=False)
    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument('--jobs', '-j', action='store', type=int, default=cpu_count)
    parser.add_argument('--tool', '-t', action='store', default='buildc',
                        choices=['buildc', 'make', 'makefile', 'ninja', 'ninjabuild', 'ninja.build'],
                        help="Sets which build tool to use. By default buildc uses, \
                             buildcloth's own build runners. Specify another build tool \
                             to use buildc as a metabuild tool.")
    parser.add_argument('--file', '-f', action='append',
                        default=list())
    parser.add_argument('--check', '-c', action='append',
                        default='mtime', choices=['mtime', 'force', 'ignore'],
                        help='for buildcloth runners, specifies which to use for testing dependency rebuilds.')

    parser.add_argument('--path', '-p', action='append',
                        default=[os.getcwd()])
    parser.add_argument('stages', nargs="*", action='store', default=[])
    args = parser.parse_args()

    sys.path.extend(args.path)

    log_level = logging.WARNING
    logging.basicConfig(level=log_level)

    if args.log is not False:
        log_level = logging.INFO
    elif args.debug:
        log_level = logging.DEBUG

    if args.log is not False and os.path.isdir(os.path.dirname(args.log)):
        logging.basicConfig(filename=args.log, level=log_level)
    else:
        logging.basicConfig(level=log_level)

    if args.file == []:
        for fn in [ 'buildc.yaml', 'buildc.yml', 'buildc.json', 'buildc.jsn' ]:
            fqpn = os.path.join(os.getcwd(), fn)
            if os.path.exists(fqpn):
                args.file.append(fqpn)

    return args

def main():
    ui = cli_ui()

    if ui.tool == 'buildc':
        stages(ui.jobs, ui.stages, ui.file, ui.check)
    elif ui.tool.startswith('make'):
        make(ui.file, ui.stages)
    elif ui.too.startswith('ninja'):
        logger.critical('ninja implementation of buildc not complete.')

if __name__ == '__main__':
    main()
