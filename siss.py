#!/usr/bin/python2.7

import httplib
import hmac
import base64
import hashlib
import unittest


IMAGE_FORMAT = "jpg"
# or 00013c9ba733ec3a61a0250d015e416cb24c00001df7_180_180
IMAGE_NAME = "00013c9ba733ec3a61a0250d015e416cb24c00001df7_180_180"


class SissException(Exception):
    def __init__(self, status, reason):
        super(SissException, self).__init__()
        self.status = status
        self.reason = reason

    def __str__(self):
        return "%d %s" % (self.status, self.reason)


class SissConnection(object):
    """Client lib for Siss Storage Service"""

    def __init__(self, address, secret_key, timeout=30):
        super(SissConnection, self).__init__()
        self.address = address
        self.secret_key = secret_key
        self.timeout = timeout
        self.conn = httplib.HTTPConnection(address, timeout=self.timeout)

    def generate_signature(self, method, host, path):
        msg = method + host + path
        hm = hmac.new(self.secret_key, msg, hashlib.sha256)
        return base64.encodestring(hm.digest()).strip()

    def put(self, content):
        auth = self.generate_signature("PUT", self.address, "/")
        self.conn.request("PUT", "/", content, {"Authorization": auth})
        res = self.conn.getresponse()
        if res.status != 200:
            raise SissException(1, "%d %s" % (res.status, res.reason))
        else:
            return res.read()

    def put_from_file(self, path):
        f = open(path, 'r')
        fid = self.put(f)
        f.close()
        return fid

    def delete(self, fid):
        uri = "/" + fid
        auth = self.generate_signature("DELETE", self.address, uri)
        self.conn.request("DELETE", uri, headers={"Authorization": auth})
        res = self.conn.getresponse()
        # must read away the buffer even it is empty
        res.read()
        if res.status != 200:
            if res.status == 404:
                raise SissException(2, "%d %s" % (res.status, res.reason))
            else:
                raise SissException(1, "%d %s" % (res.status, res.reason))

    def get(self, fid):
        uri = "/" + fid
        self.conn.request("GET", uri)
        res = self.conn.getresponse()
        if res.status != 200:
            raise SissException(1, "%d %s" % (res.status, res.reason))
        else:
            return res.read()

    def exists(self, fid):
        uri = "/" + fid
        self.conn.request("HEAD", uri)
        res = self.conn.getresponse()
        # must read away the buffer even it is empty
        res.read()
        if res.status == 200:
            return True
        elif res.status == 404:
            return False
        else:
            raise SissException(1, "%d %s" % (res.status, res.reason))

    def get_to_file(self, fid, path):
        ret = self.get(fid)
        f = open(path, 'w')
        f.write(ret)
        f.close()

    def close(self):
        self.conn.close()


class TestSiss(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_put(self):
        try:
            conn = SissConnection("127.0.0.1:8081", "85d617c7e82c1ec51ee00bec5dca17e4")
            # put from file
            fid = conn.put_from_file("./test.%s" % IMAGE_FORMAT)
            self.assertEqual(IMAGE_NAME, fid)
            # exists
            self.assertTrue(conn.exists(fid))
            # get
            conn.get(fid)
            # get to file
            conn.get_to_file(fid, "./test1.%s" % IMAGE_FORMAT)
            # delete
            # conn.delete(fid)
            conn.close()
        except SissException, e:
            self.fail(str(e))


if __name__ == '__main__':
    unittest.main()
