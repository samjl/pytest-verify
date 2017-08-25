from pytest import log, verify, set_scope, clear_scope, fixture, skip


@fixture(scope='module', autouse=True)
def m_st0(request):
    """Module scope setup and teardown functions.
    Automatically used by all test functions within module.
    """
    @clear_scope(request)  # Clear the scope when teardown is complete.
    def teardown():
        """Teardown"""
        log.high_level_step("m_st0-teardown")
        # PASS CONDITION
        verify(True, "m_st0-teardown:pass", raise_immediately=False)
    request.addfinalizer(teardown)

    @set_scope(request)  # Set the scope before executing setup.
    def setup():
        """Setup"""
        log.high_level_step("m_st0-setup")
        # PASS CONDITION
        verify(True, "m_st0-setup:pass", raise_immediately=False)
    setup()


@fixture(scope='function')
def f_st0(request):
    """Function scope setup and teardown functions.
    To apply to a test function add fixture name as test function
    argument.
    """
    @clear_scope(request)
    def teardown():
        log.high_level_step("f_st0-teardown")
        # PASS CONDITION
        verify(True, "f_st0-teardown:pass", raise_immediately=False)
        # FAIL CONDITION
        # STANDARD ASSERT FAILURE
        # assert False, "Teardown Asserting False"
    request.addfinalizer(teardown)

    @set_scope(request)
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


@fixture(scope='function')
def f_st1(request):
    @clear_scope(request)
    def teardown():
        log.high_level_step("f_st1-teardown")
        # PASS CONDITION
        verify(True, "f_st1-teardown:pass", raise_immediately=False)
        # FAIL CONDITION
        # STANDARD ASSERT FAILURE
        # assert False, "Teardown Asserting False"
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("f_st1-setup")
        # PASS CONDITION
        verify(True, "f_st1-setup:pass", raise_immediately=False)
        # SKIP
        # skip("skip during test")
        # FAIL CONDITION
        # WARNING CONDITION
        # STANDARD ASSERT FAILURE
        # assert False, "Setup Asserting False"
    setup()


def test_phases_0(f_st0):
    log.high_level_step("Test the pytest-verify plugin 0")
    log.high_level_step("Saving results with test phase and phase scope")

    log.detail_step("Test a verification that passes")
    x = True
    verify(x is True, "test0:call:test x is True (pass)")

    log.detail_step("Test a verification that fails")
    x = False
    verify(x is True, "test0:call:test x is True (fail)",
           raise_immediately=False,
           stop_at_test=True)

    log.detail_step("End of test_phases_0")


def test_phases_1(f_st0, f_st1):
    log.high_level_step("Test the pytest-verify plugin 1")
    log.high_level_step("Saving results with test phase and phase scope")

    log.detail_step("Test a verification that passes")
    x = True
    verify(x is True, "test1:call:test x is True (pass)")

    log.detail_step("Test a verification that fails")
    x = False
    verify(x is True, "test1:call:test x is True (fail)",
           raise_immediately=False, stop_at_test=True)

    log.detail_step("End of test_phases_1")
