from ali_tool.core.resolver import substitute


def test_absent_and_declared_empty_resolve_alike():
    template = "run{?model: --model {model}} {mode|fast}"
    assert substitute(template, {}) == "run fast"
    assert substitute(template, {"model": "", "mode": ""}) == "run fast"
    assert (
        substitute(template, {"model": "opus", "mode": "slow"})
        == "run --model opus slow"
    )


def test_absent_array_lookup_takes_default():
    template = "split {direction[left:-h,_:-v]}"
    assert substitute(template, {}) == "split -v"
    assert substitute(template, {"direction": ""}) == "split -v"
    assert substitute(template, {"direction": "left"}) == "split -h"


def test_optional_field_left_unset_by_parse(router):
    assert "--model" not in router.execute("FORK")
    assert router.execute("FORK opus").endswith(
        "'claude --continue --fork-session --model opus'"
    )
