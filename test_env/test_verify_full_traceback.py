from pytest import log, verify, get_saved_results


def test_logging():
    log.high_level_step("Test the verify function traceback option ("
                        "full_method_trace)")

    func = lambda x: x is True
    log.detail_step("Ensure there is no traceback for passed verifications")
    verify("Check something is true (passes) - no traceback", func, True)

    log.detail_step("Ensure default behaviour is short trace back")
    verify("Check something is true (fails) - default (short traceback)",
           func, False, raise_assertion=False)

    log.detail_step("Test no change when full_method_trace is set to False")
    verify("Check something is true (fails) - full_method_trace is False",
           func, False, raise_assertion=False, full_method_trace=False)

    def check_something():
        log.step("Checking something...")
        verify("Check something is true (fails) - in function", func, False,
               raise_assertion=False, full_method_trace=True)

    def do_something():
        log.step("Doing something")
        check_something()

    log.detail_step("Test traceback depth back to test function")
    do_something()

    log.detail_step("Test a function as condition argument")
    verify("Check something is true (fails)  - func as arg", func,
           do_something(),
           raise_assertion=False, full_method_trace=True)

    log.detail_step("Test traceback depth past test function (into pytest "
                    "source)")
    verify("Check something is true (fails) - don't stop traceback at test "
           "function", func, do_something(), raise_assertion=False,
           full_method_trace=True, stop_at_test=False)

    # Retrieve the saved results and traceback info for any failed
    # verifications.
    saved_results, saved_tracebacks = get_saved_results()
    for saved_tb in saved_tracebacks:
        log.step("* Traceback:raised: {}".format(saved_tb["raised"]))
        log.step("Traceback:complete:")
        for line in saved_tb["complete"]:
            log.step(line)

    log.detail_step("End of test")
