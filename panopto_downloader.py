import urllib.request
import sys
import os
import re
import time # for current timestemp for the filename of the final file

from queue import Queue
from threading import Thread

amount_threads = 10 # the amount of threads used to download the files (default: 10)

class DownloadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        failed_ctr = 0
        while True:
            if (failed_ctr == 0):
                try:
                    ctr = self.queue.get(timeout=3) # if there is no new element to download for 5 seconds
                except: # exit the thread
                    break
 
            try:
                # print(f"Downlading file '{ctr:05}.ts'")
                urllib.request.urlretrieve(f"{url}{ctr:05}.ts", f"temp/{ctr:05}.ts")
                failed_ctr = 0
                print(f"File '{ctr:05}.ts' downloaded")

            except urllib.error.HTTPError as e:
                if e.code == 403: # downloaded every video
                    self.queue.queue.clear() # clear the queue
                    break
                else:
                    failed_ctr += 1
                    print(f"Failed to download the file (Attempt {failed_ctr})")
                    print(e)
                    pass # try to download the file again
                    
            except Exception as e:
                failed_ctr += 1
                print(f"Failed to download the file (Attempt {failed_ctr})")
                print(e)
                pass # try to download the file again

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

print(f"Starting to download the files (with {amount_threads} threads)...")
queue = Queue()
workers = []
for x in range(amount_threads):
    workers.append(DownloadWorker(queue))
    workers[-1].deamon = True
    workers[-1].start()

for x in range(100000): # fill the queue with all possible numbers. 
                        # If a thread detects there are no more videos to download, the queue will be cleared.
    queue.put(x)

for worker in workers:  # wait until every worker thread is finished
    worker.join()
    
files = [int(f.replace(".ts", "")) for f in os.listdir("./temp/") if f.endswith(".ts")] # list all temp files and store the file numbers as integer
files.sort() # sort the list to ensure the videos parts are in the correct order
files = [f"./temp/{f:05}.ts" for f in files] # format the file numbers --> e.g. "./temp/00001.ts"

ffmpeg_string = f'ffmpeg -i \"concat:{"|".join(files)}\" -c copy -bsf:a aac_adtstoasc {final_filename}' # create the ffmpeg string to concatinate the parts

print("Concatinating files via ffmpeg...")
os.system(ffmpeg_string) # executing ffmpeg

print("Deleting temp files...")
files = [f for f in os.listdir("./temp/") if f.endswith(".ts")]
for file in files:
    os.remove(f"./temp/{file}")

print(f"Video saved as '{final_filename}'")
print("Finished! Exiting... :)")
