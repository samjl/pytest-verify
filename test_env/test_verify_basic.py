from pytest import log, verify


def test_logging():
    log.high_level_step("Test the pytest-verify plugin, basic use of verify "
                        "function")

    log.detail_step("Test a verification that passes")

    func = lambda foo: foo is True
    verify("Check something is true (passes)", func, True)

    log.detail_step("Test a verification that fails")
    verify("Check something is true (fails)", func, False,
           raise_assertion=False)

    log.detail_step("End of test")
