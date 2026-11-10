from sim.simulate import build_attack, make_parser


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
