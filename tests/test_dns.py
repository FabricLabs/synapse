# -*- coding: utf-8 -*-
# Copyright 2014-2016 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mock import Mock

from twisted.internet import defer
from twisted.names import dns, error

from synapse.http.endpoint import resolve_service

from tests.utils import MockClock

from . import unittest


@unittest.DEBUG
class DnsTestCase(unittest.TestCase):

    @defer.inlineCallbacks
    def test_resolve(self):
        dns_client_mock = Mock()

        service_name = "test_service.example.com"
        host_name = "example.com"

        answer_srv = dns.RRHeader(
            type=dns.SRV,
            payload=dns.Record_SRV(
                target=host_name,
            )
        )

        dns_client_mock.lookupService.return_value = defer.succeed(
            ([answer_srv], None, None),
        )

        cache = {}

        servers = yield resolve_service(
            service_name, dns_client=dns_client_mock, cache=cache
        )

        dns_client_mock.lookupService.assert_called_once_with(service_name)

        self.assertEquals(len(servers), 1)
        self.assertEquals(servers, cache[service_name])
        self.assertEquals(servers[0].host, host_name)

    @defer.inlineCallbacks
    def test_from_cache_expired_and_dns_fail(self):
        dns_client_mock = Mock()
        dns_client_mock.lookupService.return_value = defer.fail(error.DNSServerError())

        service_name = "test_service.example.com"

        entry = Mock(spec_set=["expires"])
        entry.expires = 0

        cache = {
            service_name: [entry]
        }

        servers = yield resolve_service(
            service_name, dns_client=dns_client_mock, cache=cache
        )

        dns_client_mock.lookupService.assert_called_once_with(service_name)

        self.assertEquals(len(servers), 1)
        self.assertEquals(servers, cache[service_name])

    @defer.inlineCallbacks
    def test_from_cache(self):
        clock = MockClock()

        dns_client_mock = Mock(spec_set=['lookupService'])
        dns_client_mock.lookupService = Mock(spec_set=[])

        service_name = "test_service.example.com"

        entry = Mock(spec_set=["expires"])
        entry.expires = 999999999

        cache = {
            service_name: [entry]
        }

        servers = yield resolve_service(
            service_name, dns_client=dns_client_mock, cache=cache, clock=clock,
        )

        self.assertFalse(dns_client_mock.lookupService.called)

        self.assertEquals(len(servers), 1)
        self.assertEquals(servers, cache[service_name])

    @defer.inlineCallbacks
    def test_empty_cache(self):
        dns_client_mock = Mock()

        dns_client_mock.lookupService.return_value = defer.fail(error.DNSServerError())

        service_name = "test_service.example.com"

        cache = {}

        with self.assertRaises(error.DNSServerError):
            yield resolve_service(
                service_name, dns_client=dns_client_mock, cache=cache
            )

    @defer.inlineCallbacks
    def test_name_error(self):
        dns_client_mock = Mock()

        dns_client_mock.lookupService.return_value = defer.fail(error.DNSNameError())

        service_name = "test_service.example.com"

        cache = {}

        servers = yield resolve_service(
            service_name, dns_client=dns_client_mock, cache=cache
        )

        self.assertEquals(len(servers), 0)
        self.assertEquals(len(cache), 0)
