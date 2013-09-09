#!/usr/bin/python2.7

import sys
import os
import io
import hmac
import hashlib
import base64
import stat
import logging
import time
import datetime
import ConfigParser

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

try:
    from PIL import Image, ImageOps
except ImportError:
    import Image
    import ImageOps


CACHE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


class SissApplication(tornado.web.Application):
    def __init__(self, options):
        tornado.web.Application.__init__(self, [(r"/(.*)", SissHandler)])
        self.options = options


class SissBaseHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ("PUT", "GET", "DELETE", "HEAD")

    def check_fid(self, fid):

        # length can be different accordingly to the image density
        if len(fid) < 44:
            return False

        for c in fid:
            # FIXME: enable it later
            #if c not in "01234567890abcdef_":        
            if c not in "01234567890abcdef_.wbp":
                return False
        return True

    def set_common_header(self):
        self.set_header("Server", "Siss/1.0")

    def generate_signature(self, method, host, path):
        msg = method + host + path
        hm = hmac.new(self.application.options["secret_key"], msg, hashlib.sha256)
        return base64.encodestring(hm.digest()).strip()

    def calc_file_md5(self, body):
        return hashlib.md5(body).hexdigest()

    def calc_file_id(self, md5, size):
        return "%04x%s%08x" % (self.application.options["server_id"], md5, size)

    def calc_file_id_with_density(self, md5, size, density):
        return "%04x%s%08x_%s_%s" % (self.application.options["server_id"], md5, size, density[0], density[1])

    def calc_file_path(self, fid):
        return os.path.join(self.application.options["store_root"], fid[4:6], fid[6:8], fid)


class SissHandler(SissBaseHandler):
    def get(self, fid):
        # verify params
        if not self.check_fid(fid):
            raise tornado.web.HTTPError(400)
            # calc metadata
        path = self.calc_file_path(fid)
        # read the file
        try:
            info = os.stat(path + ".1")
            f = open(path + ".1", 'r')
            try:
                body = f.read()
            finally:
                f.close()
        except IOError as (errno, strerror):
            if errno == 2:
                raise tornado.web.HTTPError(404)
            else:
                logging.error("Error while reading %s, %d, %s" % (path, errno, strerror))
                raise tornado.web.HTTPError(500)
                # output
        self.set_common_header()
        self.set_header("Content-Type", self.application.options["mime"])
        self.set_header("Cache-Control", "max-age=" + str(CACHE_MAX_AGE))
        self.set_header("Expires", datetime.datetime.utcfromtimestamp(info.st_mtime + CACHE_MAX_AGE))
        self.set_header("Last-Modified", datetime.datetime.utcfromtimestamp(info.st_mtime))
        self.set_header("Date", datetime.datetime.utcfromtimestamp(time.time()))
        self.write(body)
        self.finish()

    def head(self, fid):
        # verify params
        if not self.check_fid(fid):
            raise tornado.web.HTTPError(400)
            # calc metadata
        path = self.calc_file_path(fid)
        # stat a file
        if not os.path.isfile(path + ".1"):
            raise tornado.web.HTTPError(404)
            # output
        self.set_common_header()
        self.set_header("Content-Type", self.application.options["mime"])
        self.finish()

    def put(self, fid):
        # auth the request
        auth1 = self.request.headers["Authorization"]
        auth2 = self.generate_signature("PUT", self.request.headers["Host"], "/")
        if auth1 != auth2:
            raise tornado.web.HTTPError(401)

        body = self.request.body
        img = Image.open(io.BytesIO(body))
        md5 = self.calc_file_md5(body)
        fid = self.calc_file_id_with_density(
            md5,        # hash of the image
            len(body),  # image (byte of string)
            img.size    # image density in tuple (eg. (180, 180))
        )
        path = self.calc_file_path(fid)

        # store file
        if not os.path.isfile(path + ".1"):
            # create new one
            try:
                f = open(path + ".1", 'w')
                try:
                    f.write(body)
                    logging.info("Successfully write file: %s" % path)
                finally:
                    f.close()
            except IOError as (errno, strerror):
                logging.error("Error while writing %s, %d, %s" % (path, errno, strerror))
                raise tornado.web.HTTPError(500)
        else:
            # create hard link
            rc = os.stat(path + ".1")[stat.ST_NLINK]
            os.link(path + ".1", path + "." + str(rc + 1))
            logging.info("File existed: %s, new hard link is created with rc=%d" % (path, rc + 1))
        # output
        self.set_common_header()
        self.write(fid)
        self.finish()

    def delete(self, fid):
        # auth the request
        auth1 = self.request.headers["Authorization"]
        auth2 = self.generate_signature("DELETE", self.request.headers["Host"], "/" + fid)
        if auth1 != auth2:
            raise tornado.web.HTTPError(401)
            # verify params
        if not self.check_fid(fid):
            raise web.HTTPError(400)
            # calc metadata
        path = self.calc_file_path(fid)
        # unlink the file
        if not path.startswith(self.application.options["store_root"]) or \
                not os.path.isfile(path + ".1"):
            raise web.HTTPError(404)
        rc = os.stat(path + ".1")[stat.ST_NLINK]
        # unlink the largest hard link
        os.unlink(path + "." + str(rc))
        logging.info("Unlink a file: %s, with rc=%d" % (path, rc))
        # output
        self.set_common_header()
        self.finish()


def parse_conf_file(path):
    defaults = {
        "ip": "127.0.0.1",
        "port": 22222,
        "secret_key": "85d617c7e82c1ec51ee00bec5dca17e4",
        "server_id": 1,
        "store_root": "/var/siss/store",
        "image_format": "jpg",
        "image_width": 445,
        "image_quality": 85,
        "mime": "image/jpeg"
    }
    config = ConfigParser.RawConfigParser(defaults)
    config.read(path)
    options = {"ip": config.get("sissd", "ip"), "port": config.getint("sissd", "port")}
    if 1 > options["port"] > 65535:
        print "Parser conf file error, port must be 1~65535"
        sys.exit(-1)
        # secret key
    options["secret_key"] = config.get("sissd", "secret_key")
    # server id
    options["server_id"] = config.getint("sissd", "server_id")
    if 1 > options["server_id"] > 65535:
        print "Parser conf file error, server_id must be 1~65535"
        sys.exit(-1)
        # store root path
    options["store_root"] = config.get("sissd", "store_root")
    if options["store_root"][0] != '/':
        print "Parser conf file error, store_root must be abs path"
        sys.exit(-1)
        # image format
    options["image_format"] = config.get("sissd", "image_format")
    options["image_width"] = config.get("sissd", "image_width")
    options["image_quality"] = config.get("sissd", "image_quality")
    # mime
    options["mime"] = config.get("sissd", "mime")

    return options


def init_store(root_path):
    print "Initialize data store....."
    for i in range(0, 256):
        for j in range(0, 256):
            path = os.path.join(root_path, "%02x" % i, "%02x" % j)
            try:
                os.makedirs(path)
            except:
                pass
    print "...Done."


if __name__ == "__main__":
    # configures
    tornado.options.parse_command_line()
    options = parse_conf_file("/etc/sissd.conf")

    # initialize store
    init_store(options["store_root"])

    # fire a tornado application
    application = SissApplication(options)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options["port"], options["ip"])
    print "Server is listen on %s:%s" % (options["ip"], options["port"])

    # event loop
    tornado.ioloop.IOLoop.instance().start()
