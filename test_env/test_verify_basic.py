from pytest import log, verify


def test_logging():
    log.high_level_step("Test the pytest-verify plugin, basic use of verify "
                        "function")

    log.detail_step("Test a verification that passes")

    fail_condition = lambda x: x is True
    verify("Check something is true (passes)", fail_condition, True)

    log.detail_step("Test a verification that fails")
    verify("Check something is true (fails)", fail_condition, False,
           raise_assertion=False)

    log.detail_step("End of test")
