from pytest import log, verify


def test_verify_basic_usage():
    log.high_level_step("Test the pytest-verify plugin")
    log.high_level_step("Basic use of verify conditions")

    log.detail_step("Test a verification that passes")
    x = True
    verify(x is True, "test x is True (pass)")

    log.detail_step("Test a verification that fails")
    x = False
    verify(x is True, "test x is True (fail)", raise_immediately=False)

    log.detail_step("Test a function call as fail condition")

    def is_it_true(it):
        return it is True
    y = True
    verify(is_it_true(y), "test y is True (fail condition in function)",
           raise_immediately=False)

    log.detail_step("Test a verification that warns")
    x = False
    verify(x is True, "test x is True (warning)", warning=True)

    log.detail_step("Test a verification that passes initial failure check "
                    "then warns on a second condition")
    x = True
    y = False
    verify(x is True, "test x is True (initial pass)",
           warn_condition=y is True,
           warn_message="test y is True (initial pass->warning)")

    log.detail_step("Test a variable that falls within initial range but "
                    "fails a stricter warning range")
    x = 2
    verify(0 < x < 4, "test x in range",
           warn_condition=1 < x < 3,
           warn_message="test x is in a narrower range (pass)")

    x = 3
    verify(0 < x < 4, "test x in range",
           warn_condition=1 < x < 3,
           warn_message="test x is in a narrower range (warning)")

    x = 4
    verify(0 < x < 4, "test x in range (fail)",
           warn_condition=1 < x < 3,
           warn_message="test x is in a narrower range")

    log.detail_step("End of test_verify_basic_usage")
