from pytest import log, verify, fixture, skip


@fixture(scope='function')
def f_st0(request):
    def teardown():
        log.high_level_step("f_st0-teardown")
        # PASS CONDITION
        verify(True, "f_st0-teardown:pass", raise_immediately=False)
        # FAIL CONDITION
        # STANDARD ASSERT FAILURE
        # assert False, "Teardown Asserting False"
    request.addfinalizer(teardown)

    def setup():
        log.high_level_step("f_st0-setup")
        # PASS CONDITION
        verify(True, "f_st0-setup:pass", raise_immediately=False)
        # SKIP
        # skip("skip during test")
        # FAIL CONDITION
        # WARNING CONDITION
        # STANDARD ASSERT FAILURE
        # assert False, "Setup Asserting False"
    setup()


def test_phases_1(f_st0):
    log.high_level_step("Test the pytest-verify plugin")
    log.high_level_step("Basic use of verify conditions")

    log.detail_step("Test a verification that passes")
    x = True
    verify(x is True, "call:test x is True (pass)")

    log.detail_step("Test a verification that fails")
    x = False
    verify(x is True, "call:test x is True (fail)", raise_immediately=False,
           stop_at_test=True)

    # assert (x is
    #         True), "call:FOO with a ver long " \
    #               "message over 2 lines"

    log.detail_step("End of test_phases_1")


def test_phases_2(f_st0):
    log.high_level_step("Test the pytest-verify plugin")
    log.high_level_step("Basic use of verify conditions")

    log.detail_step("Test a verification that passes")
    x = True
    verify(x is True, "call:test x is True (pass)")

    log.detail_step("Test a verification that fails")
    x = False
    verify(x is True, "call:test x is True (fail)", raise_immediately=False,
           stop_at_test=True)

    # assert (x is
    #         True), "call:FOO with a ver long " \
    #               "message over 2 lines"

    log.detail_step("End of test_phases_2")
