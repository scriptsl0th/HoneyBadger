import ipaddress

from sim.simulate import HTTP_PROBES, SPOOF_SOURCES, build_attack, make_parser, probe_headers, probe_plan


def test_build_attack_cycles_templates_and_numbers_later_users():
    first = build_attack(1)
    fifth = build_attack(5)

    assert first.username == "root"
    assert fifth.username == "root-5"
    assert fifth.commands == first.commands


def test_parser_accepts_attack_count_and_delay():
    args = make_parser().parse_args(["--count", "12", "--delay", "0.25"])

    assert args.count == 12
    assert args.delay == 0.25


def test_spoof_sources_flag_defaults_off():
    assert make_parser().parse_args([]).spoof_sources is False
    assert make_parser().parse_args(["--spoof-sources"]).spoof_sources is True


def test_probe_plan_without_spoofing_sends_each_probe_once_from_the_real_address():
    plan = probe_plan(False)

    assert [probe for _, probe in plan] == list(HTTP_PROBES)
    assert {source for source, _ in plan} == {None}


def test_probe_plan_with_spoofing_sends_every_probe_from_every_source():
    plan = probe_plan(True)

    assert len(plan) == len(SPOOF_SOURCES) * len(HTTP_PROBES)
    assert {source for source, _ in plan} == set(SPOOF_SOURCES)


def test_spoof_sources_are_unique_public_addresses():
    # GeoIP skips private addresses, so every spoofed source must be globally routable.
    assert len(set(SPOOF_SOURCES)) == len(SPOOF_SOURCES)
    assert all(ipaddress.ip_address(ip).is_global for ip in SPOOF_SOURCES)


def test_probe_headers_add_forwarded_for_only_when_spoofing():
    assert probe_headers("curl/8", None) == {"User-Agent": "curl/8"}
    assert probe_headers("curl/8", "8.8.8.8") == {"User-Agent": "curl/8", "X-Forwarded-For": "8.8.8.8"}
