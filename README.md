# siss - A simple image storage system

## API

### Put a file

Request:

	PUT / HTTP/1.1
	Host: www.example.com
	Authorization:xQE0diMbLRepdf3YB+FIEXAMPLE=
	Content-Length: 65534
	[file content]

Response:

	HTTP/1.1 200 OK
	[FID]

FID Representation:

	machine_id(4bytes) + md5(32bytes) + file_size(8bytes)
	00014dc8263cf28b66502d0d7581384e527e0000434a

### Delete a file

Request:

	DELETE /[FID] HTTP/1.1
	Host: www.example.com
	Authorization:xQE0diMbLRepdf3YB+FIEXAMPLE=

Response:

	HTTP/1.1 200 OK

### Get a file

Request:

	GET /[FID] HTTP/1.1
	Host: www.example.com

Response:

	Content-Type:image/jpeg
	HTTP/1.1 200 OK
	[file content]

### File existence

Request:

	HEAD /[FID] HTTP/1.1
	Host: www.example.com

Response:

	Content-Type:image/jpeg
	HTTP/1.1 200 OK

## Getting Started

### Put a file

    import siss
	conn = SissConnection("127.0.0.1:8080", "85d617c7e82c1ec51ee00bec5dca17e4")
	# put from a file
	res = conn.put_from_file("./test.jpg")
	# put from a blob
	res = conn.put(file_blob)
	if res["status"] == 200:
	    fid = res["fid"]
	conn.close()

### Get a file

    # Notice: you can view a file directly from browser by http://127.0.0.1:8080/[fid]
    import siss
	conn = SissConnection("127.0.0.1:8080", "85d617c7e82c1ec51ee00bec5dca17e4")
	res = conn.get(fid)
	if res["status"] == 200:
	    file_blob = res["body"]
	conn.close()

### Delete a file

    import siss
	conn = SissConnection("127.0.0.1:8080", "85d617c7e82c1ec51ee00bec5dca17e4")
	res = conn.delete(fid)
	conn.close()

Note
----

In this README, sissd.conf configured for image_format=jpg & mime=image/jpeg.
It also supports other fromats and mimes.
---

