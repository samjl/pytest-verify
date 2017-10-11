from pytest import (
    log,
    verify,
    set_scope,
    clear_scope,
    fixture,
    skip
)


@fixture(scope='function')
def function_phase_assert(request):
    @clear_scope(request)
    def teardown():
        log.high_level_step("function_phase_assert-teardown")
        # PASS CONDITION
        verify(True, "function_phase_assert-teardown:pass",
               raise_immediately=False)
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("function_phase_assert-setup")
        # PASS CONDITION
        verify(True, "function_phase_assert-setup:pass",
               raise_immediately=False)
        # STANDARD ASSERT FAILURE
        assert False, "function_phase_assert-setup:standard assert"
    setup()


@fixture(scope='function')
def function_phase_fail(request):
    @clear_scope(request)
    def teardown():
        log.high_level_step("function_phase_fail-teardown")
        # PASS CONDITION
        verify(True, "function_phase_fail-teardown:pass", raise_immediately=False)
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("function_phase_fail-setup")
        # PASS CONDITION
        verify(True, "function_phase_fail-setup:pass", raise_immediately=False)
        # FAIL CONDITION
        verify(False, "function_phase_fail-setup:fail", raise_immediately=True)
    setup()


@fixture(scope='function')
def function_phase_no_saved(request):
    @clear_scope(request)
    def teardown():
        log.high_level_step("function_phase_no_saved-teardown")
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("function_phase_no_saved-setup")
    setup()


@fixture(scope='function')
def function_phase_saved_failure(request):
    @clear_scope(request)
    def teardown():
        log.high_level_step("function_phase_saved_failure-teardown")
        # PASS CONDITION
        verify(True, "function_phase_saved_failure-teardown:pass",
               raise_immediately=False)
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("function_phase_saved_failure-setup")
        # PASS CONDITION
        verify(True, "function_phase_saved_failure-setup:pass",
               raise_immediately=False)
        # FAIL CONDITION
        verify(False, "function_phase_saved_failure-setup:fail",
               raise_immediately=False)
    setup()


@fixture(scope='function')
def function_phase_warning(request):
    @clear_scope(request)
    def teardown():
        log.high_level_step("function_phase_warning-teardown")
        # PASS CONDITION
        verify(True, "function_phase_warning-teardown:pass",
               raise_immediately=False)
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("f_st1-setup")
        # PASS CONDITION
        verify(True, "function_phase_warning-setup:pass",
               raise_immediately=False)
        # WARNING CONDITION
        verify(False, "function_phase_warning-setup:warning", warning=True)
    setup()


@fixture(scope='function')
def function_phase_saved_pass(request):
    @clear_scope(request)
    def teardown():
        log.high_level_step("function_phase_saved_pass-teardown")
        # PASS CONDITION
        verify(True, "function_phase_saved_pass-teardown:pass", raise_immediately=False)
    request.addfinalizer(teardown)

    @set_scope(request)
    def setup():
        log.high_level_step("function_phase_saved_pass-setup")
        # PASS CONDITION
        verify(True, "function_phase_saved_pass-setup:pass", raise_immediately=False)
    setup()


def test_phases_setup_wrapper_1(function_phase_assert):
    log.high_level_step("test_phases_setup_wrapper_1 - unreachable")
    verify(True, "test_phases_setup_wrapper_1:call:unreachable-pass")


def test_phases_setup_wrapper_2(function_phase_fail):
    log.high_level_step("test_phases_setup_wrapper_2 - unreachable")
    verify(True, "test_phases_setup_wrapper_2:call:unreachable-pass")


def test_phases_setup_wrapper_3(function_phase_no_saved):
    log.high_level_step("test_phases_setup_wrapper_3 - path 2")
    log.detail_step("no saved results from setup function")
    verify(True, "test_phases_setup_wrapper_3:call:pass")
    log.high_level_step("test_phases_setup_wrapper_3 - call function complete")


def test_phases_setup_wrapper_4(function_phase_saved_failure):
    log.high_level_step("test_phases_setup_wrapper_4 - paths 2 and 3")
    log.detail_step("if continue_on_setup_failure is enabled the call "
                    "function will execute")
    verify(True, "test_phases_setup_wrapper_4:call:pass")
    log.high_level_step("test_phases_setup_wrapper_4 - call function complete")


def test_phases_setup_wrapper_5(function_phase_warning):
    log.high_level_step("test_phases_setup_wrapper_5 - paths 2, 4, 6")
    log.detail_step("if continue_on_setup_failure is enabled the call "
                    "function will execute")
    verify(True, "test_phases_setup_wrapper_5:call:pass")
    log.high_level_step("test_phases_setup_wrapper_5 - call function complete")


def test_phases_setup_wrapper_6(function_phase_saved_pass):
    log.high_level_step("test_phases_setup_wrapper_6 - paths 2, 5, 6")
    log.detail_step("call function will execute")
    verify(True, "test_phases_setup_wrapper_6:call:pass")
    log.high_level_step("test_phases_setup_wrapper_6 - call function complete")
