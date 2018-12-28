# ILua
# Copyright (C) 2018  guysv

# This file is part of ILua which is released under GPLv2.
# See file LICENSE or go to https://www.gnu.org/licenses/gpl-2.0.txt
# for full license details.

"""
This module parses and builds the top Jupyter
message format
"""
import json
import hmac
import uuid
import codecs
import getpass
import datetime
import hashlib

class SignatureException(Exception):
    pass

# ah "Manager", I use vague words to hide
# the fact that I should have splitted the
# class to a parser and a builder
class MessageManager(object):
    _SEPERATOR = b'<IDS|MSG>'

    _NAME_TO_SCHEME = {
        'hmac-sha256': hashlib.sha256
    }
    
    def __init__(self, sign_scheme, key):
        if key == "":
            self.hmac = None
        else:
            # Although the key is a hex-string, jupyter uses
            # it as a session key literally. Go figure..
            self.hmac = hmac.new(key=key.encode("ascii"),
                                digestmod=self._NAME_TO_SCHEME[sign_scheme])
        self.session = str(uuid.uuid4())

    def parse(self, message_parts):
        sep_i = message_parts.index(self._SEPERATOR)
        extra_ids = message_parts[:sep_i]
        data_parts = list(message_parts[sep_i+1:])
        hmac_sign = data_parts.pop(0)
        header = data_parts.pop(0)
        parent = data_parts.pop(0)
        metadata = data_parts.pop(0)
        content = data_parts.pop(0)
        # extra_buffers = data_parts # useless data?

        if self.hmac:
            d = self.hmac.copy()
            for serialized_dict in (header, parent, metadata,
                                    content):
                d.update(serialized_dict)
            if not hmac.compare_digest(d.hexdigest().encode("ascii"),
                                       hmac_sign):
                raise SignatureException("Failed to authenticate message")
        
        msg = {
            "header": json.loads(header),
            "parent": json.loads(parent),
            "metadata": json.loads(metadata),
            "content": json.loads(content)
        }

        return msg, extra_ids

    def build(self, msg_type, content, parent=None, metadata=None):
        parent = parent or {}
        metadata = metadata or {}

        header = {
            'msg_id': str(uuid.uuid4()),
            'username': getpass.getuser(),
            'session': self.session,
            'date': datetime.datetime.now().isoformat(),
            'msg_type': msg_type,
            'version': '5.3'
        }

        header = json.dumps(header).encode("utf8")
        parent = json.dumps(parent).encode("utf8")
        metadata = json.dumps(metadata).encode("utf8")
        content = json.dumps(content).encode("utf8")

        if self.hmac:
            d = self.hmac.copy()
            for serialized_dict in (header, parent, metadata,
                                    content):
                d.update(serialized_dict)
            
            hmac_sign = d.hexdigest().encode("ascii")
        else:
            hmac_sign = b""

        return [b'<IDS|MSG>', hmac_sign, header, parent, metadata,
                content]
