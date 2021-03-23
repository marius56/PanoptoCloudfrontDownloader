import requests
import sys
import os
import re
import time # for current timestemp for the filename of the final file

from queue import Queue
from threading import Thread

amount_threads = 10 # the amount of threads used to download the files (default: 10)

class DownloadWorker(Thread):
    def __init__(self, queue, thread_name):
        Thread.__init__(self)
        self.queue = queue
        self.thread_name = thread_name

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
                response = requests.get(f"{url}{ctr:05}.ts", timeout=10, stream=True) # stream the download --> chunk can be written while it is still downloading (usefull for big files)
                                                                                      # timeout = 10 seconds --> wait 10 seconds if the connection timed out
                if response.status_code == 200: # if the response is "200 OK"
                    with open(f"temp/{ctr:05}.ts", "wb") as temp_file: # write the downloaded content to a temp file
                        for chunk in response.iter_content(1024*1024):
                            temp_file.write(chunk)

                    failed_ctr = 0 # reset the counter for the failed tries
                    print(f"[{self.thread_name}] File '{ctr:05}.ts' downloaded")

                elif response.status_code == 403: # The site will response with a 403 if there are no more files to download
                    self.queue.queue.clear() # clear the queue, so the threads know, there are no more parts to download
                    break # exit the thread
                else:
                    failed_ctr += 1
                    print(f"[{self.thread_name}] Failed to download the file (Attempt {failed_ctr})")
                    print(e)
                    pass # try to download the file again

            except Exception as e:
                failed_ctr += 1
                print(f"[{self.thread_name}] Failed to download (Attempt {failed_ctr})")
                print(e)
                pass # try to download the file again

if __name__ == "__main__":
    url = input("Cloudfront url: ")
    final_filename = f"./final_{int(time.time())}.mp4"

    if os.path.isdir("temp"):
        print("Temp directory found. Deleting old files...")
        files = [f for f in os.listdir("./temp/") if f.endswith(".ts")]
        for file in files:
            os.remove(f"./temp/{file}")
    else:
        print("Creating temp directory.")
        os.mkdir("temp")

    print("Preparing url...")
    url = re.sub("/\d+.ts", "/", url)

    print(f"Starting to download the video parts (with {amount_threads} threads)...")
    queue = Queue()
    
    workers = []
    for x in range(amount_threads):
        workers.append(DownloadWorker(queue, f"Thread-{x+1:02}"))
        workers[-1].deamon = True
        workers[-1].start()

    for x in range(100000): # fill the queue with all possible numbers. 
                            # If a thread detects there are no more videos to download, the queue will be cleared.
        queue.put(x)

    for worker in workers:  # wait until every worker thread is finished
        worker.join()
    
    print(f"\nDownload finished")
    files = [int(f.replace(".ts", "")) for f in os.listdir("./temp/") if f.endswith(".ts")] # list all temp files and store the file numbers as integer
    files.sort() # sort the list to ensure the videos parts are in the correct order
    files = [f"./temp/{f:05}.ts" for f in files] # format the file numbers --> e.g. "./temp/00001.ts"

    ffmpeg_string = f'ffmpeg -hide_banner -loglevel panic -nostats -i \"concat:{"|".join(files)}\" -c copy -bsf:a aac_adtstoasc {final_filename}'
    
    print("Concatinating files via ffmpeg")
    os.system(ffmpeg_string)

    print("Deleting temp files...")
    files = [f for f in os.listdir("./temp/") if f.endswith(".ts")]
    for file in files:
        os.remove(f"./temp/{file}")

    print(f"Video saved as '{final_filename}'")
    print("Finished! Exiting... :)")
