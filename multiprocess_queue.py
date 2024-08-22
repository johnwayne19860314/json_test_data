# # Technically speaking, you are not using a multiprocessing.Queue instance, but rather a managed queue. This is implemented as a queue.Queue instance that resides in a process that is created when you call the multiprocessing.Manager() method. The subsequent call q.manager.Queue() returns a reference not to this queue but rather a reference to special queue proxy. When calls are made on this proxy instance, the method name and arguments are serialized/deserialized over to the manager process where the actual queue instance is acted upon.

# # There are a couple of issues with your current code. First, you cannot readily pass this proxy reference as a command line argument. Even if you could, I doubt it would be meaningful in the new process created with Popen.

# # Assuming you have control over the source code of multichild.py the first suggestion I would make is to take any code that is at global scope other than import statements, class definitions, method definitions, global variable definitions, etc., i.e. Python statements at global scope that are executed when the script is run and place then in a function named main (or any name you choose). If your script already looks like ...

# # ...
# def main():
#     ... # statements

# if __name__ == '__main__':
#     main()
# #... then there is nothing you need to do this source. Otherwise, reorganize your code so that when the script is invoked it just executes function main (or your chosen function name). Then you can modify your original source to use an actual multiprocessing.Queue instance, which offers better performance than a managed queue:

# import time 
# import multiprocessing

# from multi_child_1 import main as main1
# from multi_child_2 import main as main2

# if __name__ == "__main__":
#     q = multiprocessing.Queue()
#     p1 = Process(target=main1, args=(q,))
#     p1.start()
#     # Start other processes, for example:
#     p2 = Process(target=main2, args=(q,))
#     p2.start()
#     time.sleep(1) # What is this for?

#     # Wait for processes to complete:
#     p1.join()
#     p2.join()
# # If for some reason you cannot do this, then you need to create a non-standard managed queue such that when the manager is asked to create one it always returns a proxy to a singleton queue. This is an example of how your child process file would look:

# # File multi_child.py

# from multiprocessing.managers import BaseManager
# from multiprocessing import current_process
# import time

# address = "127.0.0.1"
# port = 50000
# password = "secret"

# def connect_to_manager():
#     BaseManager.register('sharable_queue')
#     manager = BaseManager(address=(address, port), authkey=password.encode('utf-8'))
#     manager.connect()
#     return manager.sharable_queue()

# if __name__ == '__main__':
#     sharable_queue = connect_to_manager()
#     while True:
#         n = sharable_queue.get()
#         if n is None:
#             # Senitnel telling us no more data
#             break
#         print(f'Process {current_process().pid} got {n}')
#         time.sleep(1)
# # And your main script would look like:

# # File main.py

# from multiprocessing.managers import BaseManager
# from queue import Queue
# from threading import Thread, Event
# from main_child import address, port, password, connect_to_manager
# from subprocess import Popen

# the_queue = None

# def get_queue():
#     """Return a singleton queue."""
#     global the_queue

#     if the_queue is None:
#         the_queue = Queue()
#     return the_queue

# def server(started_event, shutdown_event):
#     net_manager = BaseManager(address=(address, port), authkey=password.encode('utf-8'))
#     BaseManager.register('sharable_queue', get_queue)
#     net_manager.start()
#     started_event.set() # tell main thread that we have started
#     shutdown_event.wait() # wait to be told to shutdown
#     net_manager.shutdown()

# def main():
#     started_event = Event()
#     shutdown_event = Event()
#     # Run the manager in a thread, so that we can continue:
#     server_thread = Thread(target=server, args=(started_event, shutdown_event,))
#     server_thread.start()

#     # wait for manager to start:
#     started_event.wait()

#     sharable_queue = connect_to_manager()
#     print(dir(sharable_queue), sharable_queue._address_to_local)
#     sharable_queue.put(1)
#     sharable_queue.put(2)
#     # Put two sentinels since we are starting two processes:
#     sharable_queue.put(None)
#     sharable_queue.put(None)

#     # Here we are invoking main_child.py twice:
#     processes = [Popen(['python', 'main_child.py']) for _ in range(2)]
#     for process in processes:
#         process.communicate()

#     # tell manager we are through:
#     shutdown_event.set()
#     server_thread.join()

# if __name__ == '__main__':
#     main()
# # Prints:

# # Process 17500 got 1
# # Process 23512 got 2



# # multiprocessing.Pool already has a shared result-queue, there is no need to additionally involve a Manager.Queue. Manager.Queue is a queue.Queue (multithreading-queue) under the hood, located on a separate server-process and exposed via proxies. This adds additional overhead compared to Pool's internal queue. Contrary to relying on Pool's native result-handling, the results in the Manager.Queue also are not guaranteed to be ordered.

# # The worker processes are not started with .apply_async(), this already happens when you instantiate Pool. What is started when you call pool.apply_async() is a new "job". Pool's worker-processes run the multiprocessing.pool.worker-function under the hood. This function takes care of processing new "tasks" transferred over Pool's internal Pool._inqueue and of sending results back to the parent over the Pool._outqueue. Your specified func will be executed within multiprocessing.pool.worker. func only has to return something and the result will be automatically send back to the parent.

# # .apply_async() immediately (asynchronously) returns a AsyncResult object (alias for ApplyResult). You need to call .get() (is blocking) on that object to receive the actual result. Another option would be to register a callback function, which gets fired as soon as the result becomes ready.

# from multiprocessing import Pool

# def busy_foo(i):
#     """Dummy function simulating cpu-bound work."""
#     for _ in range(int(10e6)):  # do stuff
#         pass
#     return i

# if __name__ == '__main__':

#     with Pool(4) as pool:
#         print(pool._outqueue)  # DEMO
#         results = [pool.apply_async(busy_foo, (i,)) for i in range(10)]
#         # `.apply_async()` immediately returns AsyncResult (ApplyResult) object
#         print(results[0])  # DEMO
#         results = [res.get() for res in results]
#         print(f'result: {results}')       
# # Example Output:

# # <multiprocessing.queues.SimpleQueue object at 0x7fa124fd67f0>
# # <multiprocessing.pool.ApplyResult object at 0x7fa12586da20>
# # result: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
# # Note: Specifying the timeout-parameter for .get() will not stop the actual processing of the task within the worker, it only unblocks the waiting parent by raising a multiprocessing.TimeoutError.