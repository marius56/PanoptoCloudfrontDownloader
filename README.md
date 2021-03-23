To use the tool start a video hosted on Panopto, open the network tab of the browser developer tools (ofter F12) and look for a request to a subdomain of cloudfront.net (e.g. d2gerhoijh34gd.cloudfront.net) which downloads a file with the extension .ts (e.g. 00000.ts, 00012.ts, ...).

Right-click this entry, select "Copy URL" and paste this when the tool is asking for the cloudfront url.

It will create a temp folder, download the files (default: 10 threads) and use ffmpeg to concatinate the parts.
It is **important to have ffmpeg installed** on the system to make it work. 
Optionally you can download the ffmpeg binary and put it in the directory of the python tool.
