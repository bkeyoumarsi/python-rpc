# -*- coding: utf-8 -*-
"""Simple Python RPC client.

This module demonstrates documentation as specified by the `Google Python
Style Guide`_. Docstrings may extend over multiple lines. Sections are created
with a section header and a colon followed by a block of indented text.

Example:
        c = Client('127.0.0.1', 400001, 1, 2049)
        c.call(1, [(six.b('test-arg'), c.packer.pack_string)])

Todo:
    * Refine the program and arg passing to the client
    * Add auth handler to the client
    * Add documetation to the client package
    * Add to pypi repository
"""

import os
import xdrlib
import socket
import six

from random import randint

#
# RPC Definition
#

RPCVERSION = 2

CALL = 0
REPLY = 1

AUTH_NULL = 0

MSG_ACCEPTED = 0
MSG_DENIED = 1

SUCCESS = 0
PROG_UNAVAIL = 1
PROG_MISMATCH = 2
PROC_UNAVAIL = 3
GARBAGE_ARGS = 4

RPC_MISMATCH = 0
AUTH_ERROR = 1

class Client(object):
    """A simple RPC client.

    Args:
        address (str): RPC server address.
        rpc_program (int): RPC program to target.
        rpc_version (int): RPC program version.
        port (int): Port number for the RPC server.
    """

    def __init__(self, address, rpc_program, rpc_version, port):
        self.packer = xdrlib.Packer()
        self.unpacker = xdrlib.Unpacker('')
        self.address = address
        self.prog = rpc_program
        self.vers = rpc_version
        self.port = port
        self.cred = None
        self.verf = None

        self._init_socket()
        self._init_xid()

    def _init_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.address, self.port))
        except socket.error:
            raise Exception('Failed to establish a connection with the RPC server')

    def _init_xid(self):
        self.xid = randint(0, 4096)

    def _make_xid(self):
        self.xid += 1

    def _make_cred(self):
        if self.cred is None:
            self.cred = (AUTH_NULL, six.b(''))
        return self.cred

    def _make_verf(self):
        if self.verf is None:
            self.verf = (AUTH_NULL, six.b(''))
        return self.verf

    def _pack_auth(self, auth):
        flavor, stuff = auth
        self.packer.pack_enum(flavor)
        self.packer.pack_opaque(stuff)

    def _pack_callheader(self, xid, prog, vers, proc, cred, verf):
        self.packer.pack_uint(xid)
        self.packer.pack_enum(CALL)
        self.packer.pack_uint(RPCVERSION)
        self.packer.pack_uint(prog)
        self.packer.pack_uint(vers)
        self.packer.pack_uint(proc)
        self._pack_auth(cred)
        self._pack_auth(verf)

    def _unpack_auth(self):
        flavor = self.unpacker.unpack_enum()
        stuff = self.unpacker.unpack_opaque()
        return (flavor, stuff)

    def _unpack_replyheader(self):
        xid = self.unpacker.unpack_uint()
        mtype = self.unpacker.unpack_enum()
        if mtype != REPLY:
            raise Exception(
                ('no REPLY but %r') % (mtype,))
        stat = self.unpacker.unpack_enum()
        if stat == MSG_DENIED:
            stat = self.unpacker.unpack_enum()
            if stat == RPC_MISMATCH:
                low = self.unpacker.unpack_uint()
                high = self.unpacker.unpack_uint()
                raise Exception(
                    ('MSG_DENIED: RPC_MISMATCH: %r') % ((low, high),))
            if stat == AUTH_ERROR:
                stat = self.unpacker.unpack_uint()
                raise Exception(
                    ('MSG_DENIED: AUTH_ERROR: %r') % (stat,))
            raise Exception(('MSG_DENIED: %r') % (stat,))
        if stat != MSG_ACCEPTED:
            raise Exception(
                ('Neither MSG_DENIED nor MSG_ACCEPTED: %r') % (stat,))
        verf = self._unpack_auth()
        stat = self.unpacker.unpack_enum()
        if stat == PROG_UNAVAIL:
            raise Exception(('call failed: PROG_UNAVAIL'))
        if stat == PROG_MISMATCH:
            low = self.unpacker.unpack_uint()
            high = self.unpacker.unpack_uint()
            raise Exception(
                ('call failed: PROG_MISMATCH: %r') % ((low, high),))
        if stat == PROC_UNAVAIL:
            raise Exception(('call failed: PROC_UNAVAIL'))
        if stat == GARBAGE_ARGS:
            raise Exception(('call failed: GARBAGE_ARGS'))
        if stat != SUCCESS:
            raise Exception(('call failed: %r') % (stat,))
        return xid, verf

    def _init_call(self, proc, args):
        self._make_xid()
        self.packer.reset()
        cred = self._make_cred()
        verf = self._make_verf()
        self._pack_callheader(self.xid, self.prog, self.vers, proc, cred, verf)

        for arg, func in args:
            func(arg)

        return self.xid, self.packer.get_buf()

    def _sendfrag(self, last, frag):
        x = len(frag)
        if last:
            x = x | 0x80000000
        header = (six.int2byte(int(x >> 24 & 0xff)) +
                  six.int2byte(int(x >> 16 & 0xff)) +
                  six.int2byte(int(x >> 8 & 0xff)) +
                  six.int2byte(int(x & 0xff)))
        self.sock.send(header + frag)

    def _sendrecord(self, record):
        self._sendfrag(1, record)

    def _recvfrag(self):
        header = self.sock.recv(4)
        if len(header) < 4:
            raise Exception(
                ('Invalid response header from RPC server'))
        x = (six.indexbytes(header, 0) << 24 |
             six.indexbytes(header, 1) << 16 |
             six.indexbytes(header, 2) << 8 |
             six.indexbytes(header, 3))
        last = ((x & 0x80000000) != 0)
        n = int(x & 0x7fffffff)
        frag = six.b('')
        while n > 0:
            buf = self.sock.recv(n)
            if not buf:
                raise Exception(
                    ('RPC server response is incomplete'))
            n = n - len(buf)
            frag = frag + buf
        return last, frag

    def _recvrecord(self):
        record = six.b('')
        last = 0
        while not last:
            last, frag = self._recvfrag()
            record = record + frag
        return record

    def _make_call(self, proc, args):
        self.packer.reset()
        xid, call = self._init_call(proc, args)
        self._sendrecord(call)
        reply = self._recvrecord()
        self.unpacker.reset(reply)
        xid, verf = self._unpack_replyheader()

    def call(self, procedure, args=[]):
        """Initiated and make RPC call to the server.

        Args:
            procedure (int): the RPC procedure to call.
            args (list, optional): List of tuples of arguments
                and their appropriate packers.

        """
        self._make_call(procedure, args)
        res = self.unpacker.unpack_uint()
        if res != SUCCESS:
            raise Exception(os.strerror(res))

