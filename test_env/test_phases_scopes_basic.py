from pytest import (
    log,
    verify,
    set_scope,
    clear_scope,
    fixture,
    skip
)


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
        # FAIL CONDITION
        # verify(False, "m_st0-teardown:fail", raise_immediately=False)
        # SKIP
        # skip("m_st0-teardown:skip")
        # WARNING CONDITION
        # verify(False, "m_st0-teardown:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "m_st0-teardown:standard assert"
    request.addfinalizer(teardown)

    @set_scope(request)  # Set the scope before executing setup.
    def setup():
        """Setup"""
        log.high_level_step("m_st0-setup")
        # PASS CONDITION
        verify(True, "m_st0-setup:pass", raise_immediately=False)
        # FAIL CONDITION
        # verify(False, "m_st0-setup:fail", raise_immediately=False)
        # SKIP
        # skip("m_st0-setup:skip")
        # WARNING CONDITION
        # verify(False, "m_st0-setup:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "m_st0-setup:standard assert"
    setup()


@fixture(scope='class')
def c_st0(request):
    """Class scope setup and teardown functions.
    If autouse is set it is used by all tests and seems to ALL test
    functions whether they are in a class or not (same as module scope).
    """
    @clear_scope(request)  # Clear the scope when teardown is complete.
    def teardown():
        """Teardown"""
        log.high_level_step("c_st0-teardown")
        # PASS CONDITION
        verify(True, "c_st0-teardown:pass", raise_immediately=False)
        # FAIL CONDITION
        # verify(False, "c_st0-teardown:fail", raise_immediately=False)
        # SKIP
        # skip("c_st0-teardown:skip")
        # WARNING CONDITION
        # verify(False, "c_st0-teardown:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "c_st0-teardown:standard assert"
    request.addfinalizer(teardown)

    @set_scope(request)  # Set the scope before executing setup.
    def setup():
        """Setup"""
        log.high_level_step("c_st0-setup")
        # PASS CONDITION
        verify(True, "c_st0-setup:pass", raise_immediately=False)
        # FAIL CONDITION
        # verify(False, "c_st0-setup:fail", raise_immediately=False)
        # SKIP
        # skip("c_st0-setup:skip")
        # WARNING CONDITION
        # verify(False, "c_st0-setup:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "c_st0-setup:standard assert"
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
        # verify(False, "f_st0-teardown:fail", raise_immediately=False)
        # SKIP
        # skip("f_st0-teardown:skip")
        # WARNING CONDITION
        # verify(False, "f_st0-teardown:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "f_st0-teardown:standard assert"
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("f_st0-setup")
        # PASS CONDITION
        verify(True, "f_st0-setup:pass", raise_immediately=False)
        # FAIL CONDITION
        # verify(False, "f_st0-setup:fail", raise_immediately=False)
        # SKIP
        # skip("f_st0-setup:skip")
        # WARNING CONDITION
        # verify(False, "f_st0-setup:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "f_st0-setup:standard assert"
    setup()


@fixture(scope='function')
def f_st1(request):
    # @clear_scope(request)
    def teardown():
        log.high_level_step("f_st1-teardown")
        # PASS CONDITION
        verify(True, "f_st1-teardown:pass", raise_immediately=False)
        # FAIL CONDITION
        # verify(False, "f_st1-teardown:fail", raise_immediately=False)
        # SKIP
        # skip("f_st1-teardown:skip")
        # WARNING CONDITION
        # verify(False, "f_st1-teardown:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "f_st1-teardown:standard assert"
    request.addfinalizer(teardown)

    # @set_scope(request)
    def setup():
        log.high_level_step("f_st1-setup")
        # PASS CONDITION
        verify(True, "f_st1-setup:pass", raise_immediately=False)
        # FAIL CONDITION
        # verify(False, "f_st1-setup:fail", raise_immediately=False)
        # SKIP
        # skip("f_st1-setup:skip")
        # WARNING CONDITION
        # verify(False, "f_st1-setup:warning", warning=True)
        # STANDARD ASSERT FAILURE
        # assert False, "f_st1-setup:standard assert"
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

    # log.detail_step("Test a verification that fails")
    # x = False
    # verify(x is True, "test1:call:test x is True (fail)",
    #        raise_immediately=False, stop_at_test=True)

    # assert False, "test_phases_1 Asserting False"

    log.detail_step("End of test_phases_1")


class TestsToRun:
    def test_class_0(self, c_st0, f_st1):
        log.high_level_step("Test the pytest-verify plugin: test class 0")
        log.high_level_step("Saving results with test phase and phase scope")

        log.detail_step("Test a verification that passes")
        x = True
        verify(x is True, "test_class_0:call:test x is True (pass)")

        # log.detail_step("Test a verification that fails")
        # x = False
        # verify(x is True, "test1:call:test x is True (fail)",
        #        raise_immediately=False, stop_at_test=True)

        log.detail_step("End of test_class_0")

    def test_class_1(self, c_st0, f_st1):
        log.high_level_step("Test the pytest-verify plugin: test class 1")
        log.high_level_step("Saving results with test phase and phase scope")

        log.detail_step("Test a verification that passes")
        x = True
        verify(x is True, "test_class_1:call:test x is True (pass)")

        log.detail_step("End of test_class_1")
