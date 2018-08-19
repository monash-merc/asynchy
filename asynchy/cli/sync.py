# -*- coding: utf-8 -*-

"""Console script for asynchy."""
import signal
import click

from multiprocessing import cpu_count
from asynchy.asynchy import main
from asynchy.rsync import RSyncTransfer


@click.command()
@click.option("--dest", default="./",
              help="Destination directory",
              show_default=True)
@click.option("--src_prefix", default="/",
              help="Prefix to append to EPNs to create their path",
              show_default=True)
@click.option("--order", default="ASC",
              help="Order of transfers by date",
              show_default=True)
@click.option("--limit", default=50,
              help="Number of EPNs transfer",
              show_default=True)
@click.option("--retry", default=0,
              help="Number of time to retry SSH connection",
              show_default=True)
@click.option("--parallel", default=False,
              help="Use multiple processes for parallelisation",
              is_flag=True, show_default=True)
@click.option("--threads", default=cpu_count(),
              help="Number of threads to use. If parallel, the number of "
              "Python processes to use",
              show_default=True)
@click.option("--partial", is_flag=True, default=False,
              help="Enable partial transfers",
              show_default=True)
@click.option("--compress", is_flag=True, default=False,
              help="Enable compression prior to transfer",
              show_default=True)
@click.pass_context
def sync(ctx, dest, src_prefix, order, limit, retry, parallel,
         threads, partial, compress):
    """Sync data from a configured asynchy remote"""
    if parallel:
        from multiprocessing.pool import Pool
    else:
        from multiprocessing.dummy import Pool

    # disable default interrupt handlers for Pool processes
    default_int_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = Pool(processes=threads)
    rst = RSyncTransfer(
        host=ctx.obj['host'],
        user=ctx.obj['user'],
        keypath=ctx.obj['keypath'],
        port=ctx.obj['port'],
        partial=partial,
        compress=compress,
        retry=retry,
        pool=pool
    )
    signal.signal(signal.SIGINT, default_int_handler)
    main(rst, ctx.obj['db'], dest, src_prefix, order, limit)
