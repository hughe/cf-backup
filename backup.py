import datetime
import logging
import multiprocessing
import os
import queue
import shutil
import sys
import time
import typing

log = logging.getLogger(__name__)

# 1 is a generic failure.
FAILED_CHECK = 2
FAILED_SYNC = 3

def send_message(q: multiprocessing.Queue, mess) -> None:
    try:
        q.put_nowait(mess)
    except queue.Full:
        # It doesn't matter if we drop a message.  None of the
        # messages are important, they are just for the UI.  The only
        # important thing to come back from the process is the exit
        # code.
        pass 

def count_files(dirname: os.PathLike, q: multiprocessing.Queue, initial_count: bool) -> (int, int):
    count = 0
    size = 0
    for root, dirs, files in os.walk(dirname):
        count += len(files)
        size += sum(os.path.getsize(os.path.join(root, name)) for name in files)
        
        send_message(q, ('C' if initial_count else 'H', count, size))

    print("counted", count, size)

    send_message(q, ('C' if initial_count else 'H', count, size))

    return (count, size)


def backup_directory(src: os.PathLike, dst: os.PathLike, num_files: int = -1, callback=None) -> None:
    count = 0

    def do_copy(s, d):
        nonlocal count
        shutil.copy2(s, d)
        if num_files > -1:
            count += 1
            if count % 20 == 0 and callback is not None:
                callback(count)

    shutil.copytree(src, dst, copy_function=do_copy)

    if callback is not None:
        callback(count)

def backup_proc(src: os.PathLike, dst: os.PathLike, q: multiprocessing.Queue) -> None:
    """Process started by multiprocessing to backup files from src to
       dst.  Sends status reports to q.  Calls sys.exit() when done or on error."""
    num_files, total_size = count_files(src, q, True)

    def cb(c: int) -> None:
        send_message(q, ('B', num_files, c))

    start_time = time.time()
        
    backup_directory(src, dst, num_files=num_files, callback=cb)

    end_time = time.time()

    send_message(q, ('S', total_size, end_time - start_time))

    check_num_files, check_total_size = count_files(dst, q, False)

    try:
        os.sync()
    except Exception:
        # TODO: log
        sys.exit(FAILED_SYNC)
    
    q.close()

    if check_num_files != num_files:
        # TODO: log an error (should we lock?)
        sys.exit(FAILED_CHECK)

    if check_total_size != total_size:
        # TODO: log an error (should we lock?)
        sys.exit(FAILED_CHECK)

    sys.exit(0)

def make_target_directory(dst: os.PathLike) -> typing.Tuple[os.PathLike, str]:
    dst = os.path.join(dst, "SDBackup")
    now = datetime.datetime.utcnow()
    tgt = now.strftime("%Y-%m-%d-%H-%M-%S")
    dst = os.path.join(dst, tgt)
    # TODO: do something if the dir already exists.
    return (dst, tgt)
        

if __name__ == '__main__':
    import sys
    import time
    
    src = os.path.abspath(sys.argv[1])
    dst = os.path.abspath(sys.argv[2])

    q = multiprocessing.Queue(100)

    # Start the process
    p = multiprocessing.Process(target=backup_proc, args=(src, dst, q))
    p.start()

    while True:
        # Busy wait for the process to exit.
        print("sleep")
        time.sleep(1)

        drain = True
        while drain:
            # Get message tuples from the q.  Don't block if the queue
            # is empty.
            try:
                t = q.get_nowait()
                print(repr(t))
            except queue.Empty:
                drain = False

        # Try to join the process, but don't block.
        p.join(0)

        if p.exitcode is not None:
            # The process exited
            print("Child exited", p.exitcode)
            q.close()
            p.close()
            sys.exit(0)
    
    

    
    
