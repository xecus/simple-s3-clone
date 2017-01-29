easy-s3-clone
--

this is s3 clone app by python-flask.
at your own risk.

# How To Use

```
$ pip install -r requirements.txt
$ mkdir datas
$ python app.py
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger pin code: 556-844-699
127.0.0.1 - - [29/Jan/2017 01:29:20] "GET /test-bucket/?max-keys=1000&prefix&delimiter=%2F HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:23] "GET /test-bucket/?max-keys=1000&prefix&delimiter=%2F HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:24] "PUT /test-bucket/gopher.png HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:24] "GET /test-bucket/?max-keys=1000&prefix&delimiter=%2F HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:27] "GET /test-bucket/?max-keys=1000&prefix&delimiter=%2F HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:33] "PUT /test-bucket/test_dir/ HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:33] "GET /test-bucket/?max-keys=1000&prefix&delimiter=%2F HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:36] "GET /test-bucket/?max-keys=1000&prefix=test_dir%2F&delimiter=%2F HTTP/1.1" 200 -
127.0.0.1 - - [29/Jan/2017 01:29:36] "DELETE /test-bucket/test_dir/ HTTP/1.1" 204 -
127.0.0.1 - - [29/Jan/2017 01:29:36] "DELETE /test-bucket/gopher.png HTTP/1.1" 204 -
127.0.0.1 - - [29/Jan/2017 01:29:36] "GET /test-bucket/?max-keys=1000&prefix&delimiter=%2F HTTP/1.1" 200 -
```

# How to setup cyberduck

- default accessKeyId: hogehoge_user1
- default secretAccessKey: hogehoge_password1

