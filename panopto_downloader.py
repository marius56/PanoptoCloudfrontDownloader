import requests
import sys
import os
import re
import time # for current timestemp for the filename of the final file
import shutil # to concatinate the videos parts
import argparse

from queue import Queue
from threading import Thread, Event

# Special thanks to Konstantin Goretzki (https://github.com/konstantingoretzki) for the idea to just concatinate the content of the file instead of using ffmpeg! :)
class ConcatWorker(Thread): 
    def __init__(self, finished, thread_name, outputfilename):
        Thread.__init__(self)
        self.thread_name = thread_name
        self.finished = finished
        if outputfilename == None:
            self.final_filename = f"./final_{int(time.time())}.ts"
        else:
            self.final_filename = outputfilename
        
    def run(self):
        current_part = 0
        with open(self.final_filename, "wb") as outputfile:
            while True:
                # if the next part is not available, wait 2 seconds then restart the loop
                if not os.path.isfile(f"./temp/{current_part}.ts"):
                    # if there is no following part and the finished event is set, break the loop
                    if self.finished.is_set():
                        #print(f"[{self.thread_name}] Finished")
                        break
                    # If no more videos are found, wait one second and check again
                    time.sleep(1)
                    pass
           
                #print(f"[{self.thread_name}] Concatinating: {current_part}.ts")
                try:
                    with open(f"./temp/{current_part}.ts", "rb") as inputfile:
                        shutil.copyfileobj(inputfile, outputfile)

                    os.remove(f"./temp/{current_part}.ts")
                    current_part += 1
                    #print(f"[{self.thread_name}] Finished concatinating: {current_part}.ts")
                    
                except FileNotFoundError:
                    # If a file could not be found for a reason, try again
                    pass   

class DownloadWorker(Thread):
    def __init__(self, queue, thread_name, url):
        Thread.__init__(self)
        self.queue = queue
        self.thread_name = thread_name
        self.url = url

    def run(self):
        failed_ctr = 0
        while True:
            if (failed_ctr == 0):
                try:
                    ctr = self.queue.get(timeout=3) # if there is no new element to download for 3 seconds
                except: # exit the thread
                    break
            try:
                # print(f"[{self.thread_name}] Downloading file '{ctr:05}.ts'") # activate this line if you want to have a message when a download is started
                response = requests.get(f"{self.url}{ctr:05}.ts", timeout=10, stream=True) # stream the download --> chunk can be written while it is still downloading (usefull for big files)
                                                                                      # timeout = 10 seconds --> wait 10 seconds if the connection timed out
                if response.status_code == 200: # if the response is "200 OK"
                    with open(f"temp/{ctr}.tmp", "wb") as temp_file: # write the downloaded content to a temp file
                        for chunk in response.iter_content(1024*1024):
                            temp_file.write(chunk)

                    os.rename(f"temp/{ctr}.tmp", f"temp/{ctr}.ts")
                    failed_ctr = 0 # reset the counter for the failed tries
                    print(f"[{self.thread_name}] File '{ctr:05}.ts' downloaded")

                elif response.status_code == 403: # The site will response with a 403 if there are no more files to download
                    self.queue.queue.clear() # clear the queue, so the threads know, there are no more parts to download
                    break # exit the thread
                else:
                    failed_ctr += 1
                    print(f"[{self.thread_name}] Failed to download the file (Attempt {failed_ctr})")
                    pass # try to download the file again

            except Exception as e:
                failed_ctr += 1
                print(f"[{self.thread_name}] Failed to download (Attempt {failed_ctr})")
                print(e)
                pass # try to download the file again

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(metavar='URL', dest="url", help="The url of one of the video parts")
    parser.add_argument('-t', '--threads', metavar='Threads', dest="downloadthreads", default=10, type=int, help="The amount of threads to download the video parts")
    parser.add_argument('-o', '--output', metavar="Filename", dest="outputfilename", help="The name of the downloaded file. Default: final_[timestamp].ts")

    args = parser.parse_args()

    if not args.outputfilename.endswith(".ts"):
        print("The filename must have the extension .ts")
        sys.exit(1)
        
    if os.path.isdir("temp"):
        print("Temp directory found. Deleting old files...")
        files = [f for f in os.listdir("./temp/") if f.endswith(".ts")]
        for file in files:
            os.remove(f"./temp/{file}")
    else:
        print("Creating temp directory.")
        os.mkdir("temp")

    print("Preparing url...")
    # using regex to remove the tailing /00000.ts, /000001.ts, ... from the url
    args.url = re.sub("/\d+.ts$", "/", args.url)

    print(f"Starting to download the video parts (with {args.downloadthreads} threads)...")
    queue = Queue()
    
    workers = []
    for x in range(args.downloadthreads):
        workers.append(DownloadWorker(queue, f"Thread-{x+1:02}", args.url))
        workers[-1].deamon = True
        workers[-1].start()

    # fill the queue with all possible numbers. 
    # If a thread detects there are no more videos to download, the queue will be cleared.
    for x in range(1000000): 
        queue.put(x)

    quitEvent = Event()
    concatworker = ConcatWorker(quitEvent, f"Thread-Converter", args.outputfilename)
    concatworker.deamon = True
    concatworker.start()

    for worker in workers:  # wait until every worker thread is finished
        worker.join()

    print(f"\nDownload finished")

    quitEvent.set()

    print(f"Waiting for the concatination thread to finish...")
    concatworker.join()

    print(f"Concatination finished.")
    print(f"\nVideo saved as '{concatworker.final_filename}'")
