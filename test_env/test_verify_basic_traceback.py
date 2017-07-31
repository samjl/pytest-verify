from pytest import log, verify, get_saved_results


def test_basic_traceback():
    log.high_level_step("Basic traceback test")

    fail_condition = lambda x: x is True
    verify("Check something is true (passes)", fail_condition, True)
    verify("Check something is true (fails)", fail_condition, False,
           raise_assertion=False)

    log.detail_step("End of test")
