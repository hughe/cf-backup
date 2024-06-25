import multiprocessing
import os
import queue
import shutil

FAILED_CHECK = 2

def send_message(q: multiprocessing.Queue, mess) -> None:
    try:
        q.put_nowait(mess)
    except queue.Full:
        pass # It doesn't matter if we drop a message.


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


def backup_directory(src: os.PathLike, dest: os.PathLike, num_files: int = -1, callback=None) -> None:
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
    num_files, total_size = count_files(src, q, True)
    

    def cb(c: int) -> None:
        send_message(q, ('B', num_files, c))

    start_time = time.time()
        
    backup_directory(src, dst, num_files=num_files, callback=cb)

    end_time = time.time()

    send_message(q, ('S', total_size, end_time - start_time))

    check_num_files, check_total_size = count_files(dst, q, False)

    q.close()

    if check_num_files != num_files:
        # TODO: log an error (should we lock?)
        sys.exit(FAILED_CHECK)

    if check_total_size != total_size:
        # TODO: log an error (should we lock?)
        sys.exit(FAILED_CHECK)
        

if __name__ == '__main__':
    import sys
    import time
    
    src = os.path.abspath(sys.argv[1])
    dst = os.path.abspath(sys.argv[2])

    q = multiprocessing.Queue(100)

    p = multiprocessing.Process(target=backup_proc, args=(src, dst, q))

    p.start()

    while True:
        print("sleep")
        time.sleep(1)

        drain = True
        while drain:
            try:
                t = q.get_nowait()
                print(repr(t))
            except queue.Empty:
                drain = False

        p.join(0)

        if p.exitcode is not None:
            print("Child exited", p.exitcode)
            q.close()
            p.close()
            sys.exit(0)
            
                                
    

    
    
