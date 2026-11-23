"""GeoIP provider tests (no network, no database)."""

import asyncio

import pytest

from config import Settings
from geoip import IpApiProvider, is_public_ip


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "172.16.0.5", "192.168.1.10", "::1", "0.0.0.0", "not-an-ip"])
def test_non_public_addresses(ip):
    assert not is_public_ip(ip)


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "2001:4860:4860::8888"])
def test_public_addresses(ip):
    assert is_public_ip(ip)


class ExplodingCache:
    """Fails the test if the provider touches the cache (and so would go on to the network)."""

    async def get(self, ip):
        raise AssertionError(f"cache queried for {ip}")

    async def set(self, ip, info, ttl_days):
        raise AssertionError(f"cache written for {ip}")


def test_private_address_skips_cache_and_network():
    provider = IpApiProvider(cache=ExplodingCache(), settings=Settings())
    assert asyncio.run(provider.lookup("127.0.0.1")) is None
